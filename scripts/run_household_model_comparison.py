from __future__ import annotations

import argparse
from dataclasses import asdict, replace
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import random
import sys


ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "apps/api"
sys.path.insert(0, str(API_ROOT / "src"))

from movie_night_mediator.adapters import TmdbCandidateSource  # noqa: E402
from movie_night_mediator.api.recommendation_contract import (  # noqa: E402
    RecommendationShortlistRequestPayload,
    recommendation_request_from_payload,
)
from movie_night_mediator.app.backfill import ManualBackfillService  # noqa: E402
from movie_night_mediator.app.recommendation import (  # noqa: E402
    RecommendationService,
)
from movie_night_mediator.app.recommendation_snapshot import (  # noqa: E402
    RecommendationSnapshotService,
)
from movie_night_mediator.app.setup import SQLiteSetupStore  # noqa: E402
from movie_night_mediator.app.taste_memory import TasteMemoryService  # noqa: E402
from movie_night_mediator.domain import Candidate, HouseholdDefaults  # noqa: E402
from movie_night_mediator.fixtures.demo_couple import (  # noqa: E402
    DEMO_HUSBAND_PROFILE,
    DEMO_WIFE_PROFILE,
)
from movie_night_mediator.scoring import ScoringEngineId  # noqa: E402
from movie_night_mediator.storage import (  # noqa: E402
    SQLiteBackfillStore,
    SQLiteRecommendationSnapshotStore,
    SQLiteTasteLabStore,
    SQLiteTasteMemoryStore,
)
from movie_night_mediator.taste_lab import TasteLabService  # noqa: E402


OUTPUT_DIRECTORY = ROOT / ".lavish"
KEY_DIRECTORY = ROOT / ".tools/household-comparisons"
MINIMUM_PROFILE_ITEMS = 10


class _FixedCandidateSource:
    def __init__(self, candidates: tuple[Candidate, ...]) -> None:
        self._candidates = candidates

    def fetch_candidates(self, **_: object) -> tuple[Candidate, ...]:
        return self._candidates


def main() -> None:
    args = _arguments()
    comparison_id = args.comparison_id or datetime.now(UTC).strftime(
        "household-%Y%m%d-%H%M%S"
    )
    setup_store = SQLiteSetupStore()
    availability = (
        args.availability
        or setup_store.load_setup().defaults.availability_region
    )
    payload = RecommendationShortlistRequestPayload(
        sessionId=comparison_id,
        householdId=args.household_id,
        activeMode=args.mode,
        participantIds=args.profile_ids,
        shortlistSize=5,
        availabilityRegion=availability,
        source="live_tmdb",
    )
    request = recommendation_request_from_payload(payload)
    candidates = TmdbCandidateSource().fetch_candidates(
        session=request.session,
        household_defaults=HouseholdDefaults(
            default_region=request.session.region or "DE",
            default_service=request.session.service_constraint or "",
        ),
        limit=args.candidate_count,
    )
    if len(candidates) < 5:
        raise RuntimeError("The live provider returned fewer than five candidates.")
    fixed_source = _FixedCandidateSource(candidates)
    recommendation_service = _recommendation_service(
        setup_store=setup_store,
        candidate_source=fixed_source,
    )
    profile_ids = request.session.viewer_user_ids
    profile_labels = _profile_labels(setup_store, profile_ids)
    candidate_fingerprint = _candidate_fingerprint(candidates)
    engines = [
        ScoringEngineId.V2_CONTRACT,
        ScoringEngineId.V2_COLLABORATIVE,
        ScoringEngineId.V2_HYBRID,
    ]
    random.Random(comparison_id).shuffle(engines)

    paths = []
    reveal = {}
    for label, engine in zip(("A", "B", "C"), engines, strict=True):
        items = recommendation_service.recommend(
            replace(request, scoring_engine=engine)
        )
        if len(items) != 5:
            raise RuntimeError(
                f"{engine.value} produced {len(items)} of five comparable items "
                f"from {len(candidates)} live candidates."
            )
        if engine != ScoringEngineId.V2_CONTRACT and not any(
            evidence.startswith("learned_taste:")
            for item in items
            for evidence in item.dominant_positive_evidence
        ):
            raise RuntimeError(
                f"{engine.value} fell back before producing learned taste evidence."
            )
        if engine != ScoringEngineId.V2_CONTRACT:
            profile_counts = {
                profile_id: _profile_item_count(
                    items,
                    model_name=engine.value.removeprefix("v2_"),
                    user_id=profile_id,
                )
                for profile_id in profile_ids
            }
            sparse_profiles = {
                profile_id: count
                for profile_id, count in profile_counts.items()
                if count < MINIMUM_PROFILE_ITEMS
            }
            if sparse_profiles:
                raise RuntimeError(
                    f"{engine.value} cannot enter the household gate because "
                    + ", ".join(
                        f"{profile_id} has {count} mapped profile items"
                        for profile_id, count in sparse_profiles.items()
                    )
                    + f"; at least {MINIMUM_PROFILE_ITEMS} are required."
                )
        paths.append(
            {
                "label": label,
                "items": [_item_payload(item) for item in items],
            }
        )
        reveal[label] = engine.value

    generated_at = datetime.now(UTC).isoformat()
    report = {
        "comparison_id": comparison_id,
        "generated_at": generated_at,
        "candidate_fingerprint": candidate_fingerprint,
        "candidate_count": len(candidates),
        "mode": args.mode,
        "profiles": profile_labels,
        "paths": paths,
    }
    key = {
        "comparison_id": comparison_id,
        "generated_at": generated_at,
        "candidate_fingerprint": candidate_fingerprint,
        "candidate_count": len(candidates),
        "profiles": profile_ids,
        "path_to_engine": reveal,
    }
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    KEY_DIRECTORY.mkdir(parents=True, exist_ok=True)
    html_path = OUTPUT_DIRECTORY / f"{comparison_id}.html"
    key_path = KEY_DIRECTORY / f"{comparison_id}-key.json"
    html_path.write_text(_html(report))
    key_path.write_text(json.dumps(key, indent=2, sort_keys=True) + "\n")
    print(html_path)
    print(key_path)


def _recommendation_service(
    *,
    setup_store: SQLiteSetupStore,
    candidate_source: _FixedCandidateSource,
) -> RecommendationService:
    taste_memory_service = TasteMemoryService(SQLiteTasteMemoryStore())
    return RecommendationService(
        setup_store=setup_store,
        taste_lab_service=TasteLabService(
            SQLiteTasteLabStore(),
            memory_sink=taste_memory_service,
        ),
        backfill_service=ManualBackfillService(SQLiteBackfillStore()),
        taste_memory_service=taste_memory_service,
        snapshot_service=RecommendationSnapshotService(
            SQLiteRecommendationSnapshotStore()
        ),
        candidate_source=candidate_source,
    )


def _profile_labels(
    setup_store: SQLiteSetupStore,
    profile_ids: tuple[str, ...],
) -> tuple[str, ...]:
    setup_profiles = {
        profile.id: profile.label for profile in setup_store.load_setup().profiles
    }
    fallback_labels = (
        DEMO_HUSBAND_PROFILE.display_label,
        DEMO_WIFE_PROFILE.display_label,
    )
    return tuple(
        setup_profiles.get(
            profile_id,
            fallback_labels[min(index, len(fallback_labels) - 1)],
        )
        for index, profile_id in enumerate(profile_ids)
    )


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--comparison-id")
    parser.add_argument("--household-id", default="default-household")
    parser.add_argument(
        "--profile-ids",
        nargs=2,
        default=["cezary-tester", "profile-2"],
    )
    parser.add_argument(
        "--mode",
        choices=("compromise", "husband_first", "wife_first"),
        default="compromise",
    )
    parser.add_argument("--availability")
    parser.add_argument("--candidate-count", type=int, default=30)
    return parser.parse_args()


def _candidate_fingerprint(candidates: tuple[Candidate, ...]) -> str:
    payload = "\n".join(sorted(candidate.source_movie_id for candidate in candidates))
    return hashlib.sha256(payload.encode()).hexdigest()


def _item_payload(item: object) -> dict[str, object]:
    payload = asdict(item)
    return {
        "rank": payload["candidate_rank"],
        "title": payload["title"],
        "year": payload["release_year"],
        "poster_url": payload["poster_url"],
        "genres": list(payload["genres"]),
        "availability": payload["availability"],
        "why": payload["why_short"],
        "fit": payload["fit_bucket"],
        "score_a": payload["founder_score"],
        "score_b": payload["wife_score"],
    }


def _profile_item_count(
    items: tuple[object, ...],
    *,
    model_name: str,
    user_id: str,
) -> int:
    prefix = f"learned_taste:{model_name}:{user_id}:"
    for item in items:
        for evidence in item.dominant_positive_evidence:
            if evidence.startswith(prefix) and evidence.endswith("_profile_items"):
                count = evidence.removeprefix(prefix).removesuffix("_profile_items")
                if count.isdigit():
                    return int(count)
    return 0


def _html(report: dict[str, object]) -> str:
    data = json.dumps(report, separators=(",", ":")).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>WatchSignal household model comparison</title>
  <style>
    :root {{ color-scheme: dark; --bg:#04070c; --panel:rgba(10,16,26,.94); --line:rgba(255,255,255,.09); --ink:#f4f7fb; --muted:#9ba9bb; --cyan:#78f0ff; --mint:#c8f6a1; --amber:#ffd08b; --shadow:0 28px 90px rgba(0,0,0,.44); font-family:"SF Pro Text","Segoe UI Variable Text","Helvetica Neue",sans-serif; }}
    * {{ box-sizing:border-box; }} body {{ margin:0; min-height:100vh; color:var(--ink); background:radial-gradient(circle at 50% 0,rgba(120,240,255,.11),transparent 24%),radial-gradient(circle at 85% 8%,rgba(255,208,139,.08),transparent 20%),linear-gradient(180deg,#09111a,#04070c); }}
    main {{ width:min(100% - 28px,1120px); margin:0 auto; padding:26px 0 64px; }}
    header {{ max-width:760px; margin-bottom:22px; }} .eyebrow {{ color:var(--cyan); text-transform:uppercase; letter-spacing:.14em; font-size:.72rem; font-weight:800; }}
    h1 {{ margin:.45rem 0 .65rem; padding-bottom:.08em; font-size:clamp(2rem,7vw,4.4rem); line-height:1.02; letter-spacing:-.055em; }} p {{ color:var(--muted); line-height:1.55; }}
    .protocol {{ display:flex; gap:8px; flex-wrap:wrap; margin:18px 0; }} .chip {{ border:1px solid var(--line); border-radius:999px; padding:8px 11px; color:#d9e4ef; background:rgba(255,255,255,.035); font-size:.78rem; }}
    .tabs {{ display:grid; grid-template-columns:repeat(3,1fr); gap:8px; margin:20px 0 12px; position:sticky; top:8px; z-index:5; padding:6px; border:1px solid var(--line); border-radius:22px; background:rgba(4,7,12,.9); backdrop-filter:blur(16px); }}
    .tabs button {{ min-height:48px; border:0; border-radius:16px; color:var(--muted); background:transparent; font-weight:800; cursor:pointer; }} .tabs button.active {{ color:#071019; background:linear-gradient(180deg,#fff,#dffaff); }}
    .path {{ display:none; }} .path.active {{ display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:12px; }}
    .movie {{ min-width:0; overflow:hidden; border:1px solid var(--line); border-radius:24px; background:var(--panel); box-shadow:var(--shadow); }} .poster {{ width:100%; aspect-ratio:2/3; object-fit:cover; display:block; background:#121b27; }}
    .copy {{ padding:14px; }} .rank {{ color:var(--cyan); font-size:.72rem; font-weight:850; letter-spacing:.12em; text-transform:uppercase; }} h2 {{ margin:6px 0 8px; font-size:1.05rem; letter-spacing:-.02em; }} .meta {{ color:var(--muted); font-size:.78rem; line-height:1.45; }} .why {{ color:#dce6ef; font-size:.8rem; line-height:1.48; }}
    .scores {{ display:flex; gap:6px; flex-wrap:wrap; margin-top:10px; }} .score {{ padding:5px 7px; border-radius:9px; background:rgba(120,240,255,.08); color:#dffbff; font-size:.7rem; }}
    form {{ margin-top:22px; padding:20px; border:1px solid rgba(120,240,255,.18); border-radius:28px; background:linear-gradient(145deg,rgba(120,240,255,.07),rgba(255,255,255,.025)); }} fieldset {{ border:0; padding:0; margin:14px 0; display:flex; gap:10px; flex-wrap:wrap; }} label.choice {{ flex:1; min-width:120px; padding:13px; border:1px solid var(--line); border-radius:16px; background:rgba(255,255,255,.03); }} textarea {{ width:100%; min-height:100px; resize:vertical; border:1px solid var(--line); border-radius:16px; padding:13px; color:var(--ink); background:#071019; }} form button {{ width:100%; min-height:52px; border:0; border-radius:17px; margin-top:12px; background:#f4f7fb; color:#071019; font-weight:850; cursor:pointer; }}
    .boundary {{ margin-top:16px; color:var(--amber); font-size:.82rem; }}
    @media(max-width:850px) {{ main {{ width:min(100% - 24px,430px); padding-top:18px; }} .path.active {{ grid-template-columns:1fr; }} .movie {{ display:grid; grid-template-columns:106px minmax(0,1fr); }} .poster {{ height:100%; min-height:170px; }} .copy {{ padding:13px; }} }}
  </style>
</head>
<body><main>
  <header><div class="eyebrow">Founder gate - blind comparison</div><h1>Which shortlist would you trust tonight?</h1><p>All three paths saw the same people, compromise mode, watched history, and frozen live candidate pool. The model identities stay hidden until you submit a choice.</p><div class="protocol" id="protocol"></div></header>
  <nav class="tabs" aria-label="Comparison paths"></nav><section id="paths"></section>
  <form data-lavish-question="household-model-choice" id="choice-form">
    <div class="eyebrow">Your decision</div><h2>Choose the strongest complete shortlist</h2>
    <fieldset><label class="choice"><input type="radio" name="choice" value="A" required> Path A</label><label class="choice"><input type="radio" name="choice" value="B"> Path B</label><label class="choice"><input type="radio" name="choice" value="C"> Path C</label><label class="choice"><input type="radio" name="choice" value="no-winner"> No winner</label></fieldset>
    <label for="rationale">What made it better, and did either person see a veto-level miss?</label><textarea id="rationale" name="rationale" required placeholder="Mention the titles that earned or lost trust."></textarea>
    <button type="submit">Queue household decision</button><div class="boundary">This choice advances a model to default only after the reveal confirms its technical gates also passed.</div>
  </form>
</main>
<script>
const data={data};
const protocol=document.querySelector('#protocol');
[String(data.candidate_count)+' frozen candidates',data.mode.replace('_',' '),...data.profiles,'fingerprint '+data.candidate_fingerprint.slice(0,10)].forEach(text=>{{const el=document.createElement('span');el.className='chip';el.textContent=text;protocol.append(el);}});
const tabs=document.querySelector('.tabs'); const paths=document.querySelector('#paths');
data.paths.forEach((path,index)=>{{const button=document.createElement('button');button.type='button';button.textContent='Path '+path.label;button.className=index===0?'active':'';button.onclick=()=>show(path.label);tabs.append(button);const section=document.createElement('div');section.className='path '+(index===0?'active':'');section.dataset.path=path.label;path.items.forEach(item=>{{const card=document.createElement('article');card.className='movie';const poster=document.createElement('img');poster.className='poster';poster.alt='';poster.src=item.poster_url||'';const copy=document.createElement('div');copy.className='copy';const rank=document.createElement('div');rank.className='rank';rank.textContent='# '+item.rank+' - '+item.fit;const title=document.createElement('h2');title.textContent=item.title;const meta=document.createElement('p');meta.className='meta';meta.textContent=[item.year,...item.genres,item.availability].filter(Boolean).join(' - ');const why=document.createElement('p');why.className='why';why.textContent=item.why;const scores=document.createElement('div');scores.className='scores';[['Person 1',item.score_a],['Person 2',item.score_b]].forEach(([label,value])=>{{if(value!==null){{const score=document.createElement('span');score.className='score';score.textContent=label+' '+value;scores.append(score);}}}});copy.append(rank,title,meta,why,scores);card.append(poster,copy);section.append(card);}});paths.append(section);}});
function show(label){{document.querySelectorAll('.tabs button').forEach((button,index)=>button.classList.toggle('active',data.paths[index].label===label));document.querySelectorAll('.path').forEach(path=>path.classList.toggle('active',path.dataset.path===label));}}
document.querySelector('#choice-form').onsubmit=event=>{{event.preventDefault();const form=new FormData(event.currentTarget);const choice=form.get('choice');const rationale=String(form.get('rationale')||'').trim();if(!choice||!rationale)return;window.lavish.queuePrompt('Household comparison '+data.comparison_id+' choice: '+choice+'. Rationale: '+rationale,{{tag:'household-gate',text:'Choice: '+choice,queueKey:'household-model-choice',element:event.currentTarget,data:{{comparison_id:data.comparison_id,choice,rationale,candidate_fingerprint:data.candidate_fingerprint}}}});}};
</script></body></html>"""


if __name__ == "__main__":
    main()

# Founder Blockers

This file tracks founder-side setup and decisions that can block autonomous agent work.
Do not store secrets here.

## Current Status

| Item | Status | Notes |
|---|---|---|
| TMDb credentials | Done | Stored locally in `.env`, not committed. |
| OpenAI credentials | Done for later | Stored locally in `.env`, but LLM work is MVP plus 1. |
| GitHub remote | Done | Private repo exists at `czzzry/movie-night-mediator-app`. |
| Generic labels | Done | Use `Husband` and `Wife` in committed examples. |
| Product name | Done | Use `Movie Night Mediator`. |
| Real household data policy | Done | Do not commit real ratings, reactions, notes, identifiers, or watch history. |
| TMDb smoke test | Done | Credentials work and provider/language fields are reachable. |
| Prime Germany Safe Pick policy | Needs implementation | TMDb can help, but cannot fully prove audio/subtitle availability. |

## TMDb Smoke Test Finding

The local TMDb smoke test successfully fetched public metadata, Germany watch-provider buckets, and language fields.

TMDb can support:

- movie lookup
- original language
- spoken languages
- Germany watch-provider buckets such as flatrate, rent, and buy
- provider names such as Amazon Video where present

TMDb does not appear sufficient by itself to prove:

- exact Prime Video Germany subscription availability for every title
- exact English audio track availability on Prime Germany
- exact English subtitle availability on Prime Germany

## Safe Pick Implication

The MVP should not overclaim watchability.
Main recommendations should be Safe Picks only, but the implementation must define confidence honestly.

Current recommended Safe Pick policy:

- Require Germany provider data.
- Treat Amazon DE flatrate, rent, and buy as eligible when the title still passes the active language and watched-state rules.
- Treat originally English titles as language-compatible when provider availability passes.
- Treat foreign-language titles as Needs Quick Check unless English subtitles are verified by another source or manual correction.
- Store manual verified-watchable corrections so the app can learn practical availability over time.

## Repeatable Smoke Test

Run:

```sh
python3 scripts/tmdb_smoke_test.py
```

The script reads `.env` and prints only public movie metadata and provider names.

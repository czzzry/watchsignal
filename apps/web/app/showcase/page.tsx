import { demoCandidates } from "../session-fixtures";

const bestPick = demoCandidates[0];

export const metadata = {
  title: "WatchSignal Showcase",
  description: "A recruiter-facing showcase for the WatchSignal MVP.",
};

export default function ShowcasePage() {
  return (
    <main className="showcasePage">
      <section className="showcaseHero" aria-labelledby="showcase-title">
        <div className="showcaseHeroBackdrop" aria-hidden="true" />
        <div className="showcaseHeroCopy">
          <p className="showcaseKicker">WatchSignal</p>
          <h1 id="showcase-title">Stop debating. Start watching.</h1>
          <p className="showcaseLead">
            WatchSignal finds where your movie tastes overlap and gives you picks that
            keep everyone happy.
          </p>
          <div className="showcaseProofRow" aria-label="Product highlights">
            <span>Find the overlap</span>
            <span>Dodge the vetoes</span>
            <span>Keep the couch happy</span>
          </div>
        </div>

        <div className="showcasePhone" aria-label="WatchSignal app preview">
          <div className="showcasePhoneGlow" aria-hidden="true" />
          <div className="showcasePhoneChrome">
            <div className="showcaseSparkField" aria-hidden="true">
              <span />
              <span />
              <span />
              <span />
              <span />
              <span />
            </div>
            <div className="showcasePhoneTop">
              <span>It's a match</span>
              <strong>Sandy + Robin</strong>
            </div>
            <article className="showcaseWinnerCard">
              <p className="showcaseWinnerKicker">Tonight's pick</p>
              <div className="showcaseWinnerPosterWrap">
                <img src={bestPick.posterUrl} alt="" />
                <div className="showcaseScoreBadge">
                  <span>Shared signal</span>
                  <strong>88%</strong>
                </div>
              </div>
              <h2>{bestPick.title}</h2>
              <p className="showcaseWinnerMeta">
                {bestPick.year} - {bestPick.runtime} - {bestPick.genres.slice(0, 2).join(", ")}
              </p>
              <div className="showcaseWhyWon">
                <span>Why this wins</span>
                <p>
                  Sandy wanted something smart, Robin wanted emotional payoff, and nobody had to
                  surrender the remote.
                </p>
              </div>
            </article>
            <div className="showcaseCoupleSignal" aria-label="Reaction summary preview">
              <span>Sandy loved it</span>
              <div className="showcaseSignalMark" aria-label="Shared favorite">
                <span aria-hidden="true" />
              </div>
              <span>Robin is in</span>
            </div>
          </div>
        </div>
      </section>

      <section className="showcaseStory" aria-label="Showcase story beats">
        <div className="showcaseBeat">
          <span>01</span>
          <h2>Start with two moods</h2>
          <p>Each person gets a private pass, so the first opinion does not steer the room.</p>
        </div>
        <div className="showcaseBeat">
          <span>02</span>
          <h2>Find the shared center</h2>
          <p>The shortlist looks for overlap, avoids hard no votes, and keeps the night moving.</p>
        </div>
        <div className="showcaseBeat">
          <span>03</span>
          <h2>End with a yes</h2>
          <p>The result feels like a little peace treaty with a play button attached.</p>
        </div>
      </section>
    </main>
  );
}

import { demoCandidates } from "../../session-fixtures";

const arrival = {
  ...demoCandidates[0],
  posterUrl: "https://image.tmdb.org/t/p/w500/x2FJsf1ElAgr63Y3PNPtJrcmpoe.jpg",
};
const knivesOut = {
  ...demoCandidates[1],
  posterUrl: "https://image.tmdb.org/t/p/w500/pThyQovXQrw2m0s9x82twj48Jq4.jpg",
};

export const metadata = {
  title: "WatchSignal Flow",
  description: "A short walkthrough of WatchSignal's private, pass-the-phone movie flow.",
};

export default function ShowcaseFlowPage() {
  return (
    <main className="flowShowcasePage" aria-label="WatchSignal product flow demo">
      <section className="flowStage">
        <div className="flowBrand">
          <span>WatchSignal</span>
          <strong>Watch, Don't Fight</strong>
        </div>

        <div className="flowCaptionRail" aria-hidden="true">
          <p className="flowCaption flowCaptionOne">Sandy gives a private signal.</p>
          <p className="flowCaption flowCaptionTwo">Robin gets the same shortlist, without being steered.</p>
          <p className="flowCaption flowCaptionThree">WatchSignal finds the shared yes.</p>
          <p className="flowCaption flowCaptionFour">Movie night, settled. Get the popcorn.</p>
        </div>

        <div className="flowPromise" aria-hidden="true">
          <p>Stop debating.</p>
          <h1>Start watching.</h1>
        </div>

        <div className="flowPhone" aria-label="Stylized WatchSignal app flow">
          <div className="flowPhoneGlow" aria-hidden="true" />

          <article className="flowPanel flowPanelSandy" aria-label="Sandy reaction screen">
            <div className="flowPanelTop">
              <span>Sandy first</span>
              <strong>1 of 5</strong>
            </div>
            <MovieCard title={arrival.title} posterUrl={arrival.posterUrl} tag="Smart + emotional" />
            <div className="flowActionRow">
              <span className="flowAction flowActionYes">
                <span className="flowActionIcon" aria-hidden="true">♥</span>
                Interested
              </span>
              <span className="flowAction">
                <span className="flowActionIcon" aria-hidden="true">●</span>
                Maybe
              </span>
              <span className="flowAction">
                <span className="flowActionIcon" aria-hidden="true">×</span>
                No
              </span>
            </div>
            <div className="flowTap flowTapSandy">tap</div>
          </article>

          <article className="flowPanel flowPanelRobin" aria-label="Robin reaction screen">
            <div className="flowPanelTop">
              <span>Robin next</span>
              <strong>Same shortlist</strong>
            </div>
            <MovieCard title={knivesOut.title} posterUrl={knivesOut.posterUrl} tag="Funny + easy yes" />
            <div className="flowActionRow">
              <span className="flowAction">
                <span className="flowActionIcon" aria-hidden="true">♥</span>
                Interested
              </span>
              <span className="flowAction flowActionMaybe">
                <span className="flowActionIcon" aria-hidden="true">●</span>
                Maybe
              </span>
              <span className="flowAction">
                <span className="flowActionIcon" aria-hidden="true">×</span>
                No
              </span>
            </div>
            <div className="flowTap flowTapRobin">tap</div>
          </article>

          <article className="flowPanel flowPanelSignal" aria-label="Shared signal screen">
            <div className="flowSignalLogo" aria-hidden="true">
              <span />
            </div>
            <p>Reading both passes</p>
            <h2>Overlap found</h2>
            <div className="flowSignalMeters">
              <span>Sandy</span>
              <strong>88%</strong>
              <span>Robin</span>
            </div>
          </article>

          <article className="flowPanel flowPanelResult" aria-label="Final pick screen">
            <div className="flowPanelTop">
              <span>It's a match</span>
              <strong>Sandy + Robin</strong>
            </div>
            <div className="flowWinnerPoster">
              <img src={arrival.posterUrl} alt="" />
              <div>Shared signal 88%</div>
            </div>
            <h2>{arrival.title}</h2>
            <p>
              Sandy wanted something smart.
              Robin wanted emotional payoff.
              Nobody had to surrender the remote.
            </p>
          </article>
        </div>

        <div className="flowTimeline" aria-hidden="true">
          <span />
          <span />
          <span />
          <span />
        </div>
      </section>
    </main>
  );
}

function MovieCard({
  title,
  posterUrl,
  tag,
}: {
  title: string;
  posterUrl: string;
  tag: string;
}) {
  return (
    <div className="flowMovieCard">
      <img src={posterUrl} alt="" />
      <div>
        <p>{tag}</p>
        <h2>{title}</h2>
      </div>
    </div>
  );
}

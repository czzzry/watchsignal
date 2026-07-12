import Image from "next/image";

export default function CreditsPage() {
  return (
    <main className="creditsPage">
      <a className="creditsBack" href="/">
        ← Back to WatchSignal
      </a>
      <section className="creditsCard">
        <p className="eyebrow">Data credits</p>
        <h1>Movie metadata and artwork</h1>
        <Image
          alt="The Movie Database (TMDB)"
          className="tmdbLogo"
          height={133}
          src="/tmdb-logo.svg"
          width={185}
        />
        <p>
          This product uses the TMDB API but is not endorsed or certified by
          TMDB.
        </p>
        <p>
          Live movie metadata and poster images are supplied by{" "}
          <a href="https://www.themoviedb.org">The Movie Database (TMDB)</a>.
          Fixture mode uses deterministic local examples instead.
        </p>
      </section>
    </main>
  );
}

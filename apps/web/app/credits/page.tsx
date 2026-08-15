import Image from "next/image";
import Link from "next/link";
import { WatchSignalIcon } from "../ui/watchsignal-icons";
import { WatchSignalBrand } from "../ui/primitives";
import styles from "./credits.module.css";

const sourceRows = [
  {
    icon: "film" as const,
    label: "Movies",
    owner: "TMDB",
    detail: "Titles, years, runtimes, genres, synopses, cast, posters, and backdrops.",
  },
  {
    icon: "play" as const,
    label: "Where to watch",
    owner: "JustWatch",
    detail: "Region-specific provider availability, retrieved through the TMDB API. Services and availability can change.",
  },
  {
    icon: "sparkles" as const,
    label: "Your matches",
    owner: "WatchSignal",
    detail: "Ranking, Match Index, score gaps, recommendation reasons, layout, and icons.",
  },
] as const;

export default function CreditsPage() {
  return (
    <main className={styles.page} data-watchsignal-credits>
      <header className={styles.topBar}>
        <WatchSignalBrand />
        <Link className={styles.backLink} href="/">
          <WatchSignalIcon name="arrow-left" />
          <span>Back to WatchSignal</span>
        </Link>
      </header>

      <div className={styles.content}>
        <section className={styles.intro} aria-labelledby="credits-title">
          <div className={styles.tmdbMark}>
            <Image
              alt="The Movie Database (TMDB)"
              className={styles.tmdbLogo}
              height={133}
              priority
              src="/tmdb-logo.svg"
              width={185}
            />
          </div>
          <div>
            <h1 id="credits-title">Data &amp; credits</h1>
            <p>What comes from our movie source, and what WatchSignal creates.</p>
          </div>
        </section>

        <section className={styles.sourceList} aria-label="Data source ownership">
          {sourceRows.map((row) => (
            <article className={styles.sourceRow} key={row.label}>
              <span className={styles.rowIcon} aria-hidden="true">
                <WatchSignalIcon name={row.icon} />
              </span>
              <div>
                <div className={styles.rowHeading}>
                  <h2>{row.label}</h2>
                  <span>{row.owner}</span>
                </div>
                <p>{row.detail}</p>
              </div>
            </article>
          ))}
        </section>

        <section className={styles.attribution} aria-labelledby="tmdb-attribution-title">
          <h2 id="tmdb-attribution-title">TMDB attribution</h2>
          <p>
            This product uses the TMDB API but is not endorsed or certified by
            TMDB.
          </p>
          <p>
            Demo mode uses a deterministic local catalog for product testing.
            Recognizable movie metadata and imagery remain attributed to TMDB
            where used.
          </p>
        </section>
      </div>

      <footer className={styles.pageFooter}>
        <span>WatchSignal</span>
        <span>Movie data and imagery by TMDB · Provider availability by JustWatch</span>
      </footer>
    </main>
  );
}

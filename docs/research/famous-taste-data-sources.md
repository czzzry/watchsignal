# Famous taste data sources

Research date: 2026-08-23.

## Executive finding

The idea is feasible, but the public data divides into two very different products.

- A few people have 100 or more explicit positive selections, which is enough for a real person-specific retrieval pool.
- Many excellent filmmakers have about 50 explicit selections, which is enough for a useful themed candidate pool but not a complete model of their taste.
- Most famous-person interviews and ballots contain only 4 to 15 selections, so they should act as a temporary taste nudge rather than a replacement profile.
- Public availability is not the same as permission to ingest.
  Criterion, BFI, Letterboxd, and RogerEbert.com all restrict copying, scraping, exporting, or database compilation in their published terms.

The safest launch is a small, manually curated, permission-cleared set that stores only normalized movie identifiers and source provenance.
The interface can then offer both `Use this person's taste` and `Just show me their picks`.

## Named launch roster

### Deep profiles, about 50 or more explicit positive selections

| Person | Approximate usable depth | What the source actually says | Primary source | Recommendation |
| --- | ---: | --- | --- | --- |
| Edgar Wright | 1,000 | Explicit favorite movies, assembled by Wright and Sam DiSalle and now published by Letterboxd Crew. | [Letterboxd Crew list](https://letterboxd.com/crew/list/edgar-wrights-1000-favorite-movies/) | Best deep-profile pilot if reuse permission is obtained. |
| Roger Ebert | 362 | Unranked “Great Movies,” chosen for love, artistry, history, and influence rather than as a strict favorites ranking. The first three books contain 100 essays each and the final volume contains 62. | [Ebert's explanation](https://www.rogerebert.com/great-movies/great-movie-great-movies-ii-introduction), [final volume](https://www.rogerebert.com/features/exclusive-roger-eberts-the-great-movies-iv-in-print-for-the-first-time), [collection](https://www.rogerebert.com/great-movies) | Strong critic composite, but label it “Roger Ebert's Great Movies,” not “everything Ebert liked.” |
| Mike Flanagan | 250 | His self-maintained profile has a “Flanagan's Favorites: Top 250” list. He says he does not rate movies and uses a heart for films he particularly enjoyed. | [Mike Flanagan profile](https://letterboxd.com/flanaganfilm/) | Excellent living-filmmaker profile if Letterboxd grants access. |
| Michael Haneke | 100 | LaCinetek's official account publishes a list explicitly titled “100 favorite films.” | [LaCinetek list](https://letterboxd.com/lacinetek/list/michael-hanekes-list-of-100-favorite-films/) | Strong deep-profile pilot if LaCinetek grants reuse. |
| Martin Scorsese | Two 50-film lists | LaCinetek publishes one formative list and one alternative list, together representing roughly 100 list entries before deduplication. | [LaCinetek profile](https://www.lacinetek.com/fr-en/director-list/martin-scorsese-5), [official formative list](https://letterboxd.com/lacinetek/list/martin-scorseses-list-of-50-formative-films/) | Strong deep-profile pilot, but preserve “formative” versus “later discovery” as separate signals. |
| Bong Joon-ho, Guillermo del Toro, Damien Chazelle, David Cronenberg, Pete Docter, Todd Haynes, Hirokazu Kore-eda, Kiyoshi Kurosawa, Park Chan-wook, Lynne Ramsay, Kelly Reichardt, Paul Schrader, Céline Sciamma, Sean Baker, Joachim Trier, Justine Triet, Paul Verhoeven, Wim Wenders, and John Woo | About 50 each | LaCinetek says each associated filmmaker composes an ideal film library of around 50 films and identifies 154 participating filmmakers. | [LaCinetek About and full roster](https://www.lacinetek.com/fr/about), [directors' directory](https://www.lacinetek.com/fr-en) | Best launch pool for a broad director filter, subject to permission. |

LaCinetek is the strongest coherent source for a launch catalogue.
Its rules say selections are works that shaped or strongly affected the filmmaker, the filmmaker cannot choose their own work, and list order may be preference, chronology, alphabetic, or no meaningful order at all.
Rank must therefore be stored as `unknown` unless a particular list says otherwise.
[LaCinetek publishes those rules directly](https://www.lacinetek.com/fr/about).

### Sparse profiles, about 4 to 15 selections

| Source and examples | Depth | Meaning | Primary source | Recommended use |
| --- | ---: | --- | --- | --- |
| BFI Sight and Sound ballots: Martin Scorsese, Sofia Coppola, Bong Joon-ho, Barry Jenkins, Edgar Wright, Wes Anderson, Ari Aster, John Carpenter, Guillermo del Toro, and hundreds more | Usually 10 | “Greatest films,” not a complete favorites history. The 2022 directors' poll received ballots from 480 directors. | [BFI method](https://www.bfi.org.uk/sight-and-sound/directors-100-greatest-films-all-time), [all voters](https://www.bfi.org.uk/sight-and-sound/greatest-films-all-time/all-voters), [Scorsese](https://www.bfi.org.uk/sight-and-sound/greatest-films-all-time/all-voters/martin-scorsese), [Coppola](https://www.bfi.org.uk/sight-and-sound/greatest-films-all-time/all-voters/sofia-coppola), [Bong](https://www.bfi.org.uk/sight-and-sound/greatest-films-all-time/all-voters/bong-joon-ho), [Jenkins](https://www.bfi.org.uk/sight-and-sound/greatest-films-all-time/all-voters/barry-jenkins), [Wright](https://www.bfi.org.uk/sight-and-sound/greatest-films-all-time/all-voters/edgar-wright) | High-confidence context nudge or an extra signal added to a deeper profile. |
| Criterion Top 10: John Carpenter, Richard Linklater, Barry Levinson, Whit Stillman, and many more | Usually about 10 | Favorites chosen from the Criterion Collection, so the available catalogue strongly shapes the result. | [Criterion Top 10 directory](https://www.criterion.com/current/category/8-top-10-lists), [Linklater example](https://www.criterion.com/current/top-10-lists/42-richard-linklaters-top-10), [Carpenter example](https://www.criterion.com/current/top-10-lists/853-john-carpenter-s-top-10) | Context nudge, with the label “Criterion picks.” |
| Criterion Closet Picks: Christopher Nolan, Sofia Coppola, Yorgos Lanthimos, Jim Jarmusch, Ari Aster, David Cronenberg, Bong Joon-ho, Guillermo del Toro, and others | Commonly about 4 to 8 products | In-person selections from the Criterion Closet. Entries can be box sets rather than one movie. | [Criterion Closet Picks](https://www.criterion.com/closet-picks), [search directory](https://www.criterion.com/closet-picks/search) | Context nudge only. Expand box sets deliberately rather than pretending each product is one pick. |
| Letterboxd Four Favorites | 4 per interviewee | Direct, high-precision answers captured in interviews, but too sparse to define a standalone taste profile. | [Letterboxd's explanation](https://letterboxd.com/journal/featured-lists-explainer/), [official interview example](https://letterboxd.com/crew/story/four-favorites-with-the-cast-and-director/) | Context nudge and “show their four picks.” |

## Quentin Tarantino

I did not find an authoritative, first-party Tarantino corpus of 50 or 100 explicit favorites that is suitable for ingestion.

BFI confirms that Tarantino participated in its 2012 directors' poll, and BFI articles identify individual choices such as *His Girl Friday* and *Rolling Thunder*.
Those sources support a small, high-confidence profile, not the large online compilations commonly labeled “Tarantino's favorite movies.”
[BFI's 2012 poll release](https://www2.bfi.org.uk/sites/bfi.org.uk/files/downloads/bfi-press-release-hitchcocks-vertigo-topples-citizen-kane-to-become-new-greatest-film-of-all-time-2012-08-01.pdf), [BFI on *His Girl Friday*](https://www.bfi.org.uk/features/flirting-screwball), and [BFI on *Rolling Thunder*](https://www.bfi.org.uk/lists/great-action-film-every-year-1924-now) are the strongest primary provenance found.

Recommendation: do not launch Tarantino as a deep profile by silently merging interviews, podcast discussions, yearly lists, influences, and second-hand compilations.
Launch him only as a clearly labeled small collection until a source owner or Tarantino representative provides a curated list or approves a compiled dataset.

## Signal meanings must remain separate

| Signal | What can safely be inferred | What must not be inferred |
| --- | --- | --- |
| Favorite | Strong positive affinity at the time of selection. | That every omitted movie is disliked. |
| Greatest | Canon judgment or professional assessment. | That it is the person's preferred movie-night choice. |
| Formative or influential | The movie affected the person's work or development. | That they currently want to watch similar films. |
| Closet pick | They selected a Criterion product in that visit. | That it is a complete or unbiased taste sample. |
| Viewing log | They watched the movie. | That they liked it. |
| Heart, positive review, or named favorites list | Positive preference, with strength depending on the person's stated usage. | A comparable numeric rating across different people. |

This distinction matters for public Letterboxd accounts.
For example, Sean Baker's profile describes his activity as a viewing log and contains almost no ratings, while Mike Flanagan explicitly explains that his hearts mark particular enjoyment and publishes named favorites lists.
[Sean Baker's profile](https://letterboxd.com/lilfilm/) and [Mike Flanagan's profile](https://letterboxd.com/flanaganfilm/) make those differences visible.

## Access, API, and reuse constraints

| Provider | Official machine access | Published restriction | Maintainable path |
| --- | --- | --- | --- |
| Letterboxd | API access is request-only. Member RSS feeds cover new diary entries, reviews, and lists, and members can export their own account data. | Letterboxd says it is not granting API access for recommendation, LLM, private, or personal projects. Its terms prohibit exporting other users' content, significant indexes, and automated scraping without authorization. | Ask Letterboxd and the list owner for written permission. Do not build the feature by scraping. [API policy](https://letterboxd.com/api-beta/access/), [terms](https://letterboxd.com/legal/terms-of-use/). |
| Criterion | No public list API or download was found in the official directories. | Criterion forbids copying or publishing its content and explicitly forbids collecting or compiling service data by manual or automated means. | Request permission or manually receive a title-only seed list from Criterion or the participant. [Terms, sections 5.1, 5.2, and 5.8](https://www.criterion.com/terms). |
| BFI | The ballots are publicly browsable as structured web pages, but no official ballot download or public API was found on the poll pages. | BFI limits site content to personal, non-commercial use and prohibits copying, publishing, licensing, or creating derivative works without authorization. | Ask BFI to license a normalized ballot extract. [Terms, section 2](https://www.bfi.org.uk/terms-use). |
| LaCinetek | Lists are publicly browsable, and LaCinetek also republishes many as lists under its official Letterboxd account. No documented public API or bulk download was found in its directory or About page. | The rendered official Terms page does not provide an affirmative data-reuse license. | This is the best partner to approach for a licensed 154-director seed catalogue. [About](https://www.lacinetek.com/fr/about), [directory](https://www.lacinetek.com/fr-en), [Terms](https://www.lacinetek.com/fr-en/terms). |
| RogerEbert.com | No public list API or download was found. | Its terms prohibit republishing, database compilation, scraping, and data extraction without written permission. | Ask for permission to use a title-only “Great Movies” index. [Terms](https://www.rogerebert.com/terms-of-use). |

Movie titles, source commentary, images, list arrangement, and a compiled database can have different rights holders.
The product should store source URLs and attribution even when title identifiers are normalized through TMDB.
It should not copy essays, video frames, Criterion artwork, BFI comments, or profile photos without an explicit license.

## Recommended product contract

This is a product recommendation derived from the source structure above.

1. Store one record per `person + movie + source`, with `signal_type`, `list_label`, `source_url`, `source_date`, `rank_semantics`, and `permission_status`.
2. Keep source meanings separate instead of converting every selection into the same numeric “like.”
3. Offer three explicit modes: `Pick from their list`, `Use their taste as inspiration`, and `Show me their picks`.
4. `Pick from their list` restricts the candidate pool to attributed selections, then lets WatchSignal's existing household model, tonight constraints, availability rules, and diversity guardrails rank that pool.
5. The switch to list-only ranking should depend on how many mapped, unseen, available selections remain after filtering, not the raw published list size.
6. A sensible first hypothesis is to default to list-only when at least 15 eligible titles remain, offer both modes when 5 to 14 remain, and explain that the exact shelf is too small when fewer than 5 remain.
7. `Use their taste as inspiration` creates a session-only positive curator lens from the selected movies and retrieves related movies from the wider catalogue before the household scorer runs.
8. A sparse lens should retrieve neighbors around each individual anchor, while a larger list can support a robust aggregate item-embedding vector with popularity down-weighting.
9. The curator lens must never be written into either household member's durable Taste Lab profile and must never interpret an omitted movie as a dislike.
10. `Show me their picks` bypasses recommendation ranking and displays the attributed source list, with optional availability, watched, and sort filters controlled by the user.
11. Display a plain-language provenance label such as `100 favorites published by LaCinetek` or `10 greatest-film ballot picks from BFI`.
12. Result explanations must distinguish `A published pick by this person` from `Inspired by this person's picks`.
13. If a requested mode cannot produce enough eligible films, show that limitation rather than silently falling back to popular movies or another data source.
14. Never describe an automatically assembled composite as the person's taste unless every component is clearly sourced and the merge rule is visible.

## Validation gate

The inspiration mode should not ship merely because its recommendations look plausible in a few examples.
For each deep profile, hide a portion of the known selections, build the curator lens from the rest, and measure whether it retrieves the held-out selections above a popularity-only baseline.
The product test should then compare household acceptance, novelty, and list diversity against ordinary WatchSignal recommendations.
This evidence can show that the lens carries signal, but it cannot prove that the public list represents the person's complete private taste.

## Bottom line

There is enough high-quality data to prototype the experience with Edgar Wright, Michael Haneke, Martin Scorsese, Mike Flanagan, Roger Ebert, and a licensed subset of LaCinetek's 50-film directors.
There is also enough sparse data for many recognizable filmmakers through BFI, Criterion, and Letterboxd Four Favorites.
The principal blocker is reuse permission, not data discovery.
Tarantino should remain a small, explicitly sourced nudge until a genuinely authoritative deep profile exists or is commissioned.

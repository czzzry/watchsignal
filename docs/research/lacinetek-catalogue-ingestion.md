# LaCinetek catalogue ingestion

Research and live-source audit date: 2026-08-24.

## Executive finding

LaCinetek currently exposes 158 first-party filmmaker taste profiles that WatchSignal can ingest as a local snapshot.

- 154 are living or affiliated filmmaker lists.
- 4 are separate archival "Films of their lives" profiles for Chantal Akerman, Stanley Kubrick, Akira Kurosawa, and François Truffaut.
- 156 profiles currently contain at least one selection.
- Claire Simon and Valérie Donzelli are present in the roster but their current list responses contain no movie IDs.
- The complete 158-profile source contains 8,761 selection references across 159 list segments and 3,788 unique LaCinetek movie IDs.
- The 154 affiliated profiles contribute 8,206 top-level references plus Martin Scorsese's 178 references in two named secondary lists, for 8,384 affiliated-profile references in total.
- The 4 archival profiles contribute another 377 references.
- 3,786 unique movie IDs resolve to current film records.
- Two stale movie IDs are still referenced by lists but return no film record.

This is not a guessed or community-assembled dataset.
LaCinetek says participating filmmakers compose their own ideal film libraries from works that shaped them or had a major impact on their work, and that a new filmmaker list is added monthly.
[LaCinetek explains the collection and names all 154 affiliated filmmakers on its About page](https://www.lacinetek.com/fr/about).

The practical recommendation is to ingest all 158 profiles, retain the 4 archival profiles as a separately labeled type, and expose only the 156 non-empty profiles to random selection.
The import should be an offline, versioned snapshot rather than 158 live requests from the app.

## Source structure

### Roster

The server-rendered payload on the [French LaCinetek directory](https://www.lacinetek.com/fr) contains two arrays:

- `props.lists.fr.lists`: 154 affiliated profiles.
- `props.lists.fr.lifeLists`: 4 archival profiles.

Each roster entry exposes:

- list ID;
- director ID;
- localized display name, first name, and last name;
- localized profile slug;
- `isLifeList`;
- a `female` flag;
- director image URLs and image types.

The list ID, director ID, and slug are unique across all 158 records in the audited French payload.
Use the list ID as the source-profile identity and the director ID for relationships such as `recommendersIds`.
Do not use the localized name or slug as the database key.

### One filmmaker's actual list

LaCinetek's own profile page requests `GET /fetch-list/{localized-slug}` with a `language` header.
For example, the public [Bong Joon-ho profile](https://www.lacinetek.com/fr/la-liste-de/bong-joon-ho) is backed by [its first-party JSON list response](https://www.lacinetek.com/fetch-list/bong-joon-ho).

The response exposes these list-level fields across the current corpus:

`availabilities`, `categories`, `comments`, `dateUpdated`, `description`, `descriptionShort`, `director`, `female`, `firstname`, `id`, `inverted`, `lastname`, `letterId`, `linkRewrite`, `metaDescription`, `metaTitle`, `name`, `otherLists`, `parent`, `products`, and `searchName`.

The nested `director` record exposes `id`, `name`, `linkRewrite`, `description`, `descriptionShort`, `images`, and `realisations`.
All 158 profiles currently have a long biography and an `avatar_large` portrait.
Short biographies are present for 141 profiles, and `realisations` filmography references are present for 115.

Every profile response exposes a top-level `products` array of ordered LaCinetek product IDs, although that array may be empty.
For every profile except Martin Scorsese, it is the only or default segment.
Scorsese's top-level array is empty and `otherLists` contains a 73-film "Liste formative" segment and a 105-film "Liste alternative" segment.
Both segment labels must be preserved because they carry source meaning.

### Film records

LaCinetek's list UI resolves product IDs through `GET /fetch-films/{JSON-encoded-array-of-ids}` with a `country` header.
The site's bundle also exposes the single-record form `GET /fetch-film/{id}`.
A two-record example is [the first-party batch response for product IDs 395 and 753](https://www.lacinetek.com/fetch-films/%5B395%2C753%5D).
The exact construction used in the audit was `https://www.lacinetek.com/fetch-films/${encodeURIComponent(JSON.stringify(ids))}` with `country: FR`.
For `['2521', '2883']`, the exact URL is [this encoded batch request](https://www.lacinetek.com/fetch-films/%5B%222521%22%2C%222883%22%5D).
It returns the complete record for 2521 and silently omits unresolved ID 2883.

The live endpoint preserved request order among resolved IDs in forward and reversed three-ID checks.
That behavior is not documented, so the importer should still index responses by `id` and reconstruct source order from each list's own product array.

Prefer that same-origin batch endpoint over a bare query to the underlying Kinow GraphQL service.
In a comparison against the same 154-profile source, a GraphQL request without the site's full request context omitted 36 otherwise valid product IDs across 55 list references, including product IDs 2521, 2519, 2513, and 2533.
All four examples resolve through `/fetch-films` as ordinary visible film records.
The same-origin endpoint is therefore the stronger definition of what the current LaCinetek list page can hydrate.

The current batch response exposes these fields across the corpus:

`accessModes`, `actors`, `categories`, `classification`, `countries`, `countriesAvailability`, `dateUpdated`, `description`, `descriptionShort`, `director`, `directorGender`, `directorImage`, `directorsIds`, `duration`, `expirationDate`, `hideInCatalog`, `hideInProduction`, `id`, `idAllocine`, `images`, `inCollection`, `inMonthSelection`, `inMovements`, `inTreasure`, `linkRewrite`, `name`, `origin`, `original_title`, `publicationDate`, `recommendersIds`, `searchActors`, `searchDirector`, `searchName`, `subtitles`, `type`, `videos`, and `year`.

For WatchSignal's local taste catalogue, the durable core is:

- LaCinetek product ID;
- localized and original titles;
- release year;
- credited director name and director IDs;
- source list ID, source segment, and source position;
- source URL and ingestion timestamp;
- current poster or image URL if retained;
- current record status, including unresolved source references.

Availability, prices, access modes, and country flags are volatile commerce data and should not be treated as part of the person's taste.
A selected movie can remain in a filmmaker's list even when LaCinetek cannot currently offer it, which is an intentional part of LaCinetek's published model.
[The About page states that unavailable selections remain listed even when rights cannot be acquired](https://www.lacinetek.com/fr/about).

## Order is not a preference rank

Preserve source order, but never convert position 1 into a stronger preference than position 50.

LaCinetek says each filmmaker freely chooses the list order.
It may be preference order, chronological order, alphabetical order by title or director, or have no interpretable order.
[LaCinetek documents those order possibilities directly](https://www.lacinetek.com/fr/about).

Recommended contract:

- store `source_position` exactly as published;
- store `rank_semantics: "unknown"` by default;
- store Scorsese's `source_segment` as `formative` or `alternative`;
- use every selection as an explicit positive source signal of equal default strength;
- do not infer dislike from an omitted movie;
- do not present source order as a countdown or ranked top list unless the individual profile explicitly says it is ranked.

## Locale and identity quirks

The French, English, and German France-market directories each contain the same 158 list IDs with no duplicate display names inside a locale.
The identity is stable, but the presentation is not.

- English changes 5 display names and 31 slugs compared with French.
- German changes 4 display names and 2 slugs compared with French.
- Bong Joon-ho is `bong-joon-ho` in French but `joon-ho-bong` on the English profile.
- Some French slugs contain legacy suffixes or trailing hyphens, such as `agnes-varda-36`, `david-cronenberg-`, and `ken-loach-`.
- Some source names contain a vertical bar used by LaCinetek's formatter, such as `Kleber | Mendonça Filho` and `Jaco | Van Dormael`.
- Some records represent pairs, including Dominique Abel and Fiona Gordon, the Larrieu brothers, and Nakache and Toledano.
- Names include non-ASCII letters and non-breaking spaces.

Normalize whitespace and Unicode to NFC for search, remove the source formatter's ` | ` separator for display, and keep the untouched source string for provenance.
Never reconstruct another locale's URL from a French name.
Read each locale's published slug or use the French canonical URLs below.

LaCinetek profile pages publish country-language alternates and a page-specific canonical URL.
For example, [Bong Joon-ho's French profile](https://www.lacinetek.com/fr/la-liste-de/bong-joon-ho) declares French, English, and German alternates for France, Belgium, and Luxembourg.

## Reproducible and respectful ingestion

Run ingestion as an explicit offline data update, never in a user's request path.

1. Fetch `https://www.lacinetek.com/fr` once and parse the JSON inside the `__NEXT_DATA__` script element.
2. Concatenate `props.lists.fr.lists` and `props.lists.fr.lifeLists`.
3. Assert 158 unique list IDs, 158 unique director IDs, and 158 unique French slugs for the 2026-08-24 baseline.
4. Fetch `/fetch-list/{slug}` with `language: fr` at no more than four concurrent requests, a short delay between dispatches, a descriptive user agent, a 30-second timeout, and at most three bounded retries.
5. Assert that every returned list ID and slug matches its roster record.
6. Flatten `products` as the `main` segment and flatten every `otherLists[].products.items` array as its own named segment.
7. Preserve each array index as the one-based `source_position` without interpreting it as rank.
8. Deduplicate the resulting product IDs for metadata retrieval while retaining every list membership record.
9. Fetch `/fetch-films/{encoded JSON array}` in batches of at most 40 IDs with `country: FR`, again at no more than four concurrent requests.
10. Treat an omitted product record as an explicit unresolved source reference, not as permission to delete the list membership or fabricate a title.
11. Normalize Unicode to NFC and collapse source whitespace before matching or hashing.
12. Store the source's `dateUpdated`, the source URL, the ingestion timestamp, and the validation summary with the generated catalogue.
13. Perform any TMDB identity matching after this source snapshot is complete, and retain the LaCinetek ID and source URL beside the matched TMDB ID.
14. Publish the generated local catalogue atomically only when every invariant passes.

LaCinetek says a new list is normally added monthly, so a manually triggered monthly refresh is sufficient.
Cache raw responses during one run so retries and validation never refetch the same profile unnecessarily.
The endpoint is a public internal endpoint used by LaCinetek's own page, not a documented stability-guaranteed public API, so endpoint drift must fail the import visibly.

The audited Next.js build was `F2Gk6p8vDcaeey9Vl62Os`.
The list-page code for that build requests `/fetch-list/{slug}`, while the shared film loader requests `/fetch-film/{id}` and `/fetch-films/{ids}`.
[The first-party list-page bundle](https://www.lacinetek.com/_next/static/chunks/5bc2a9ac939aa7bc6af94e2bb310d710bf46e6de.806ae31c7a6320209780.js) and [film-loader bundle](https://www.lacinetek.com/_next/static/chunks/a911e1a0f3fa8e952662b3a552537f1fd6712f19.2e2200f32cbef226634b.js) expose those request paths.

## Completeness proof from the live audit

The 2026-08-24 audit used French source data, four concurrent requests, 100 milliseconds between dispatches, batches of 40 film IDs, three bounded retries, and no authenticated access.

| Check | Result |
| --- | ---: |
| Affiliated profiles | 154 |
| Archival profiles | 4 |
| Total profiles | 158 |
| Unique list IDs | 158 |
| Unique director IDs | 158 |
| Unique French slugs | 158 |
| Profile responses fetched | 158 |
| List ID mismatches | 0 |
| Slug mismatches | 0 |
| List segments | 159 |
| Selection references | 8,761 |
| Affiliated top-level selection references | 8,206 |
| Affiliated secondary-list references | 178 |
| Total affiliated-profile references | 8,384 |
| Archival-profile references | 377 |
| Unique product IDs referenced | 3,788 |
| Film records resolved | 3,786 |
| Unresolved product IDs | 2 |
| Selection references whose film records resolve | 8,748 |
| Duplicate product IDs inside one segment | 0 |
| Profiles with portraits | 158 |
| Profiles with long biographies | 158 |
| Profiles with short biographies | 141 |
| Profiles with filmography references | 115 |
| Minimum selections in one profile | 0 |
| Median selections in one profile | 53 |
| Maximum selections in one profile | 178 |

Only 21 profiles contain exactly 50 references, so `about 50` must not become a schema constraint.
Two profiles are empty in the current source: Claire Simon, list ID 1456, and Valérie Donzelli, list ID 3303.
Martin Scorsese has the maximum of 178 references across two named segments.

Two referenced movie IDs do not resolve:

- Product ID `2883` appears three times, in Bertrand Tavernier at position 76, Robin Campillo at position 51, and Aki Kaurismäki at position 54.
- Product ID `2888` appears ten times, in Laurent Cantet, Christoph Hochhäusler, James Gray, Jerry Schatzberg, Lodge Kerrigan, Luc Dardenne, Mahamat-Saleh Haroun, Catherine Corsini, Dario Argento, and Albert Dupontel.

The batch endpoint omits both records, and the single-film endpoint returns HTTP 200 with an empty body for both.
The import should retain thirteen unresolved membership rows for auditability and exclude them from recommendation candidates until they resolve.

### Deterministic checksums

All strings were normalized to Unicode NFC and internal whitespace was collapsed before hashing.
Each logical record was tab-separated, records were newline-separated with a final newline, and SHA-256 was used.

| Dataset | Canonical record form and sort | SHA-256 |
| --- | --- | --- |
| Roster | `list_id, display_name, french_slug, director_id`, sorted by numeric list ID | `4f4e6e568c1bbc8e1a466759498942f611a44bf0e1089f8f1547d72ae4944534` |
| Ordered selections | `list_id, segment, source_position, product_id`, sorted by numeric list ID, segment, then position | `b570614b5ed9297c8e6402e87054985151e3be4439ff5fa81ec07d9afb05577e` |
| Resolved French film identities | `product_id, localized_title, original_title, year, director`, sorted by numeric product ID | `5f941273244a96e8cda2a02fd728f7b31aa22a1cbbadf646777f8dec4c9522cf` |

These checksums are a dated completeness baseline, not permanent constants.
A future monthly refresh should be allowed to change them only after the import reports which profiles, memberships, or film identities changed.

## Canonical French profile roster

The following 158 URLs are the current French profile URLs published by the [official LaCinetek directory](https://www.lacinetek.com/fr).
The four archival profiles are marked separately.

| Person | Type | List ID | Director ID | Canonical profile |
| --- | --- | ---: | ---: | --- |
| Abel Ferrara | Affiliated | 877 | 6236 | [abel-ferrara](https://www.lacinetek.com/fr/la-liste-de/abel-ferrara) |
| Agnès Jaoui | Affiliated | 566 | 6384 | [agnes-jaoui](https://www.lacinetek.com/fr/la-liste-de/agnes-jaoui) |
| Agnès Varda | Affiliated | 532 | 2863 | [agnes-varda-36](https://www.lacinetek.com/fr/la-liste-de/agnes-varda-36) |
| Agnieszka Holland | Affiliated | 755 | 10706 | [agnieszka-holland](https://www.lacinetek.com/fr/la-liste-de/agnieszka-holland) |
| Aki Kaurismäki | Affiliated | 569 | 2721 | [aki-kaurismaeki](https://www.lacinetek.com/fr/la-liste-de/aki-kaurismaeki) |
| Akira Kurosawa | Archival | 688 | 2993 | [akira-kurosawa-](https://www.lacinetek.com/fr/la-liste-de/akira-kurosawa-) |
| Alain Chabat | Affiliated | 539 | 13692 | [alain-chabat](https://www.lacinetek.com/fr/la-liste-de/alain-chabat) |
| Alain Guiraudie | Affiliated | 542 | 8968 | [alain-guiraudie](https://www.lacinetek.com/fr/la-liste-de/alain-guiraudie) |
| Albert Dupontel | Affiliated | 844 | 15044 | [albert-dupontel](https://www.lacinetek.com/fr/la-liste-de/albert-dupontel) |
| Albert Serra | Affiliated | 2466 | 19878 | [albert-serra](https://www.lacinetek.com/fr/la-liste-de/albert-serra) |
| Alejandro Amenábar | Affiliated | 3487 | 13360 | [alejandro-amenabar](https://www.lacinetek.com/fr/la-liste-de/alejandro-amenabar) |
| Alexandre Astier | Affiliated | 1662 | 16827 | [alexandre-astier](https://www.lacinetek.com/fr/la-liste-de/alexandre-astier) |
| Alice Diop | Affiliated | 1699 | 17155 | [alice-diop](https://www.lacinetek.com/fr/la-liste-de/alice-diop) |
| Alice Rohrwacher | Affiliated | 1116 | 15829 | [alice-rohrwacher](https://www.lacinetek.com/fr/la-liste-de/alice-rohrwacher) |
| Alice Winocour | Affiliated | 3633 | 22314 | [alice-winocour](https://www.lacinetek.com/fr/la-liste-de/alice-winocour) |
| Amat Escalante | Affiliated | 582 | 12543 | [amat-escalante-42](https://www.lacinetek.com/fr/la-liste-de/amat-escalante-42) |
| Andreas Dresen | Affiliated | 3264 | 21913 | [andreas-dresen](https://www.lacinetek.com/fr/la-liste-de/andreas-dresen) |
| Apichatpong Weerasethakul | Affiliated | 533 | 6828 | [apichatpong-weerasethakul](https://www.lacinetek.com/fr/la-liste-de/apichatpong-weerasethakul) |
| Arnaud Desplechin | Affiliated | 516 | 6155 | [arnaud-despleschin](https://www.lacinetek.com/fr/la-liste-de/arnaud-despleschin) |
| Arnaud et Jean-Marie Larrieu | Affiliated | 577 | 11707 | [arnaud-et-jean-marie-larrieu-96](https://www.lacinetek.com/fr/la-liste-de/arnaud-et-jean-marie-larrieu-96) |
| Arthur Harari | Affiliated | 1975 | 18826 | [arthur-harari](https://www.lacinetek.com/fr/la-liste-de/arthur-harari) |
| Atom Egoyan | Affiliated | 552 | 4264 | [atom-egoyan](https://www.lacinetek.com/fr/la-liste-de/atom-egoyan) |
| Bertrand Blier | Affiliated | 547 | 2874 | [bertrand-blier](https://www.lacinetek.com/fr/la-liste-de/bertrand-blier) |
| Bertrand Bonello | Affiliated | 509 | 6816 | [bertrand-bonello](https://www.lacinetek.com/fr/la-liste-de/bertrand-bonello) |
| Bertrand Tavernier | Affiliated | 531 | 6328 | [bertrand-tavernier](https://www.lacinetek.com/fr/la-liste-de/bertrand-tavernier) |
| Bong Joon-ho | Affiliated | 508 | 6312 | [bong-joon-ho](https://www.lacinetek.com/fr/la-liste-de/bong-joon-ho) |
| Bruce LaBruce | Affiliated | 953 | 15345 | [bruce-labruce](https://www.lacinetek.com/fr/la-liste-de/bruce-labruce) |
| Bruno Podalydès | Affiliated | 559 | 10484 | [bruno-podalydes](https://www.lacinetek.com/fr/la-liste-de/bruno-podalydes) |
| Caroline Link | Affiliated | 713 | 14850 | [caroline-link](https://www.lacinetek.com/fr/la-liste-de/caroline-link) |
| Catherine Corsini | Affiliated | 574 | 11523 | [catherine-corsini-33](https://www.lacinetek.com/fr/la-liste-de/catherine-corsini-33) |
| Cédric Klapisch | Affiliated | 525 | 3444 | [cedric-klapisch](https://www.lacinetek.com/fr/la-liste-de/cedric-klapisch) |
| Céline Sciamma | Affiliated | 530 | 6817 | [celine-sciamma](https://www.lacinetek.com/fr/la-liste-de/celine-sciamma) |
| Chantal Akerman | Archival | 894 | 4535 | [chantal-akerman](https://www.lacinetek.com/fr/la-liste-de/chantal-akerman) |
| Christian Petzold | Affiliated | 567 | 11005 | [christian-petzold-69](https://www.lacinetek.com/fr/la-liste-de/christian-petzold-69) |
| Christian Rouaud | Affiliated | 529 | 6818 | [christian-rouaud](https://www.lacinetek.com/fr/la-liste-de/christian-rouaud) |
| Christoph Hochhäusler | Affiliated | 511 | 6827 | [christoph-hochhausler](https://www.lacinetek.com/fr/la-liste-de/christoph-hochhausler) |
| Christophe Gans | Affiliated | 519 | 6819 | [christophe-gans](https://www.lacinetek.com/fr/la-liste-de/christophe-gans) |
| Christophe Honoré | Affiliated | 590 | 13457 | [christophe-honore-3](https://www.lacinetek.com/fr/la-liste-de/christophe-honore-3) |
| Claire Simon | Affiliated | 1456 | 7518 | [claire-simon](https://www.lacinetek.com/fr/la-liste-de/claire-simon) |
| Claude Lelouch | Affiliated | 554 | 6982 | [claude-lelouch-95](https://www.lacinetek.com/fr/la-liste-de/claude-lelouch-95) |
| Clément Cogitore | Affiliated | 584 | 11954 | [clement-cogitore-53](https://www.lacinetek.com/fr/la-liste-de/clement-cogitore-53) |
| Corneliu Porumboiu | Affiliated | 587 | 13324 | [corneliu-porumboiu-56](https://www.lacinetek.com/fr/la-liste-de/corneliu-porumboiu-56) |
| Costa Gavras | Affiliated | 513 | 6820 | [costa-gavras](https://www.lacinetek.com/fr/la-liste-de/costa-gavras) |
| Cristian Mungiu | Affiliated | 526 | 6826 | [cristian-mungiu](https://www.lacinetek.com/fr/la-liste-de/cristian-mungiu) |
| Dag Johan Haugerud | Affiliated | 3809 | 22648 | [dag-johan-haugerud](https://www.lacinetek.com/fr/la-liste-de/dag-johan-haugerud) |
| Damien Chazelle | Affiliated | 586 | 13283 | [damien-chazelle-91](https://www.lacinetek.com/fr/la-liste-de/damien-chazelle-91) |
| Dario Argento | Affiliated | 580 | 2974 | [dario-argento-99](https://www.lacinetek.com/fr/la-liste-de/dario-argento-99) |
| David Cronenberg | Affiliated | 3143 | 4842 | [david-cronenberg-](https://www.lacinetek.com/fr/la-liste-de/david-cronenberg-) |
| Diane Kurys | Affiliated | 2968 | 18671 | [diane-kurys](https://www.lacinetek.com/fr/la-liste-de/diane-kurys) |
| Dominik Moll | Affiliated | 2464 | 18609 | [dominik-moll](https://www.lacinetek.com/fr/la-liste-de/dominik-moll) |
| Dominique et Fiona Abel & Gordon | Affiliated | 1141 | 16154 | [dominique-et-fiona-abel-gordon](https://www.lacinetek.com/fr/la-liste-de/dominique-et-fiona-abel-gordon) |
| Elia Suleiman | Affiliated | 1551 | 6846 | [elia-suleiman-](https://www.lacinetek.com/fr/la-liste-de/elia-suleiman-) |
| Emmanuel Mouret | Affiliated | 3721 | 17213 | [emmanuel-mouret](https://www.lacinetek.com/fr/la-liste-de/emmanuel-mouret) |
| Emmanuelle Bercot | Affiliated | 1025 | 15414 | [emmanuelle-bercot](https://www.lacinetek.com/fr/la-liste-de/emmanuelle-bercot) |
| Fatih Akin | Affiliated | 2073 | 12206 | [fatih-akin](https://www.lacinetek.com/fr/la-liste-de/fatih-akin) |
| Felix Van Groeningen | Affiliated | 1772 | 17524 | [felix-van-groeningen](https://www.lacinetek.com/fr/la-liste-de/felix-van-groeningen) |
| Francis Veber | Affiliated | 2924 | 2597 | [francis-veber](https://www.lacinetek.com/fr/la-liste-de/francis-veber) |
| François Ozon | Affiliated | 563 | 10784 | [francois-ozon-76](https://www.lacinetek.com/fr/la-liste-de/francois-ozon-76) |
| François Truffaut | Archival | 572 | 2418 | [francois-truffaut-41](https://www.lacinetek.com/fr/la-liste-de/francois-truffaut-41) |
| Gérard Krawczyk | Affiliated | 541 | 8915 | [gerard-krawczyk](https://www.lacinetek.com/fr/la-liste-de/gerard-krawczyk) |
| Gilles Lellouche | Affiliated | 3693 | 22352 | [gilles-lelouche](https://www.lacinetek.com/fr/la-liste-de/gilles-lelouche) |
| Guillaume Brac | Affiliated | 2172 | 19349 | [guillaume-brac](https://www.lacinetek.com/fr/la-liste-de/guillaume-brac) |
| Guillaume Nicloux | Affiliated | 1091 | 15472 | [guillaume-nicloux](https://www.lacinetek.com/fr/la-liste-de/guillaume-nicloux) |
| Guillermo del Toro | Affiliated | 3429 | 12567 | [guillermo-del-toro](https://www.lacinetek.com/fr/la-liste-de/guillermo-del-toro) |
| Hirokazu Kore-eda | Affiliated | 517 | 6825 | [hirokazu-kore-eda](https://www.lacinetek.com/fr/la-liste-de/hirokazu-kore-eda) |
| Ildikó Enyedi | Affiliated | 3694 | 22353 | [ildiko-enyedi](https://www.lacinetek.com/fr/la-liste-de/ildiko-enyedi) |
| Ira Sachs | Affiliated | 521 | 6824 | [ira-sachs](https://www.lacinetek.com/fr/la-liste-de/ira-sachs) |
| Jaco Van Dormael | Affiliated | 589 | 13456 | [jaco-van-dormael-76](https://www.lacinetek.com/fr/la-liste-de/jaco-van-dormael-76) |
| Jacques Audiard | Affiliated | 507 | 6295 | [jacques-audiard](https://www.lacinetek.com/fr/la-liste-de/jacques-audiard) |
| Jacques Doillon | Affiliated | 515 | 2935 | [jacques-doillon](https://www.lacinetek.com/fr/la-liste-de/jacques-doillon) |
| James Gray | Affiliated | 520 | 5049 | [james-gray](https://www.lacinetek.com/fr/la-liste-de/james-gray) |
| Jean-Charles Hue | Affiliated | 3237 | 21886 | [jean-charles-hue](https://www.lacinetek.com/fr/la-liste-de/jean-charles-hue) |
| Jean-Pierre Bekolo | Affiliated | 1372 | 16393 | [jean-pierre-bekolo](https://www.lacinetek.com/fr/la-liste-de/jean-pierre-bekolo) |
| Jean-Pierre Dardenne | Affiliated | 555 | 4661 | [jean-pierre-dardenne-63](https://www.lacinetek.com/fr/la-liste-de/jean-pierre-dardenne-63) |
| Jean-Pierre Jeunet | Affiliated | 514 | 6821 | [jean-pierre-jeunet](https://www.lacinetek.com/fr/la-liste-de/jean-pierre-jeunet) |
| Jerry Schatzberg | Affiliated | 536 | 6961 | [jerry-schatzberg](https://www.lacinetek.com/fr/la-liste-de/jerry-schatzberg) |
| Jessica Hausner | Affiliated | 585 | 13234 | [jessica-hausner](https://www.lacinetek.com/fr/la-liste-de/jessica-hausner) |
| Joachim Lafosse | Affiliated | 1919 | 18024 | [joachim-lafosse](https://www.lacinetek.com/fr/la-liste-de/joachim-lafosse) |
| Joachim Trier | Affiliated | 540 | 8858 | [joachim-trier](https://www.lacinetek.com/fr/la-liste-de/joachim-trier) |
| Joanna Hogg | Affiliated | 2306 | 19374 | [joanna-hogg](https://www.lacinetek.com/fr/la-liste-de/joanna-hogg) |
| João Pedro Rodrigues | Affiliated | 573 | 10498 | [joao-pedro-rodrigues-79](https://www.lacinetek.com/fr/la-liste-de/joao-pedro-rodrigues-79) |
| John Cameron Mitchell | Affiliated | 2465 | 17224 | [john-cameron-mitchell](https://www.lacinetek.com/fr/la-liste-de/john-cameron-mitchell) |
| John Woo | Affiliated | 565 | 3270 | [john-woo](https://www.lacinetek.com/fr/la-liste-de/john-woo) |
| Jonás Trueba | Affiliated | 1621 | 16716 | [jonas-trueba](https://www.lacinetek.com/fr/la-liste-de/jonas-trueba) |
| José Luis Guerín | Affiliated | 543 | 9182 | [jose-luis-guerin](https://www.lacinetek.com/fr/la-liste-de/jose-luis-guerin) |
| Justine Triet | Affiliated | 588 | 14278 | [justine-triet-77](https://www.lacinetek.com/fr/la-liste-de/justine-triet-77) |
| Jutta Brückner | Affiliated | 715 | 14229 | [jutta-bruckner](https://www.lacinetek.com/fr/la-liste-de/jutta-bruckner) |
| Kelly Reichardt | Affiliated | 3632 | 12878 | [kelly-reichardt](https://www.lacinetek.com/fr/la-liste-de/kelly-reichardt) |
| Ken Loach | Affiliated | 2680 | 6002 | [ken-loach-](https://www.lacinetek.com/fr/la-liste-de/ken-loach-) |
| Kiyoshi Kurosawa | Affiliated | 535 | 6476 | [kiyoshi-kurosawa](https://www.lacinetek.com/fr/la-liste-de/kiyoshi-kurosawa) |
| Kleber Mendonça Filho | Affiliated | 591 | 14279 | [kleber-mendonca-filho-13](https://www.lacinetek.com/fr/la-liste-de/kleber-mendonca-filho-13) |
| Laurent Cantet | Affiliated | 510 | 3757 | [laurent-cantet](https://www.lacinetek.com/fr/la-liste-de/laurent-cantet) |
| Leos Carax | Affiliated | 551 | 7886 | [leos-carax](https://www.lacinetek.com/fr/la-liste-de/leos-carax) |
| Lodge Kerrigan | Affiliated | 538 | 8726 | [lodge-kerrigan](https://www.lacinetek.com/fr/la-liste-de/lodge-kerrigan) |
| Louis Garrel | Affiliated | 3488 | 22255 | [louis-garrel](https://www.lacinetek.com/fr/la-liste-de/louis-garrel) |
| Luc Dardenne | Affiliated | 556 | 4662 | [luc-dardenne](https://www.lacinetek.com/fr/la-liste-de/luc-dardenne) |
| Luc Moullet | Affiliated | 528 | 6822 | [luc-moullet](https://www.lacinetek.com/fr/la-liste-de/luc-moullet) |
| Lucile Hadzihalilovic | Affiliated | 1889 | 4611 | [lucile-hadzihalilovic](https://www.lacinetek.com/fr/la-liste-de/lucile-hadzihalilovic) |
| Lukas Dhont | Affiliated | 758 | 15040 | [lukas-dhont](https://www.lacinetek.com/fr/la-liste-de/lukas-dhont) |
| Lynne Ramsay | Affiliated | 524 | 6829 | [lynne-ramsay](https://www.lacinetek.com/fr/la-liste-de/lynne-ramsay) |
| Mahamat-Saleh Haroun | Affiliated | 558 | 10347 | [mahamat-saleh-haroun-80](https://www.lacinetek.com/fr/la-liste-de/mahamat-saleh-haroun-80) |
| Maren Ade | Affiliated | 553 | 10106 | [maren-ade](https://www.lacinetek.com/fr/la-liste-de/maren-ade) |
| Mariano Llinás | Affiliated | 1052 | 15470 | [mariano-llinas](https://www.lacinetek.com/fr/la-liste-de/mariano-llinas) |
| Marie Losier | Affiliated | 3454 | 18820 | [marie-losier](https://www.lacinetek.com/fr/la-liste-de/marie-losier) |
| Marjane Satrapi | Affiliated | 561 | 10680 | [marjane-satrapi](https://www.lacinetek.com/fr/la-liste-de/marjane-satrapi) |
| Martin Scorsese | Affiliated | 578 | 2572 | [martin-scorsese-3](https://www.lacinetek.com/fr/la-liste-de/martin-scorsese-3) |
| Michael Haneke | Affiliated | 2857 | 3992 | [michael-haneke](https://www.lacinetek.com/fr/la-liste-de/michael-haneke) |
| Michel Hazanavicius | Affiliated | 522 | 6823 | [michel-hazanavicius](https://www.lacinetek.com/fr/la-liste-de/michel-hazanavicius) |
| Michel Ocelot | Affiliated | 937 | 15276 | [michel-ocelot](https://www.lacinetek.com/fr/la-liste-de/michel-ocelot) |
| Miguel Gomes | Affiliated | 548 | 9743 | [miguel-gomes](https://www.lacinetek.com/fr/la-liste-de/miguel-gomes) |
| Nabil Ayouch | Affiliated | 564 | 10858 | [nabil-ayouch](https://www.lacinetek.com/fr/la-liste-de/nabil-ayouch) |
| Nadav Lapid | Affiliated | 523 | 7739 | [nadav-lapid](https://www.lacinetek.com/fr/la-liste-de/nadav-lapid) |
| Nanni Moretti | Affiliated | 571 | 2451 | [nanni-moretti-43](https://www.lacinetek.com/fr/la-liste-de/nanni-moretti-43) |
| Naomi Kawase | Affiliated | 576 | 10332 | [naomi-kawase-63](https://www.lacinetek.com/fr/la-liste-de/naomi-kawase-63) |
| Nicolas Philibert | Affiliated | 545 | 3667 | [nicolas-philibert-7](https://www.lacinetek.com/fr/la-liste-de/nicolas-philibert-7) |
| Nicole Garcia | Affiliated | 1321 | 16299 | [nicole-garcia](https://www.lacinetek.com/fr/la-liste-de/nicole-garcia) |
| Noémie Lvovsky | Affiliated | 549 | 4689 | [noemie-lvovsky](https://www.lacinetek.com/fr/la-liste-de/noemie-lvovsky) |
| Olivier Assayas | Affiliated | 512 | 2696 | [olivier-assayas](https://www.lacinetek.com/fr/la-liste-de/olivier-assayas) |
| Olivier et Éric Nakache & Toledano | Affiliated | 581 | 12108 | [olivier-et-eric-nakache-toledano](https://www.lacinetek.com/fr/la-liste-de/olivier-et-eric-nakache-toledano) |
| Otar Iosseliani | Affiliated | 3596 | 14109 | [otar-iosseliani-](https://www.lacinetek.com/fr/la-liste-de/otar-iosseliani-) |
| Park Chan-wook | Affiliated | 544 | 9308 | [park-chan-wook](https://www.lacinetek.com/fr/la-liste-de/park-chan-wook) |
| Pascale Ferran | Affiliated | 518 | 6157 | [pascale-ferran](https://www.lacinetek.com/fr/la-liste-de/pascale-ferran) |
| Patrice Leconte | Affiliated | 1408 | 6446 | [patrice-leconte](https://www.lacinetek.com/fr/la-liste-de/patrice-leconte) |
| Patricia Mazuy | Affiliated | 527 | 5220 | [patricia-mazuy](https://www.lacinetek.com/fr/la-liste-de/patricia-mazuy) |
| Paul Schrader | Affiliated | 1009 | 3785 | [paul-schrader](https://www.lacinetek.com/fr/la-liste-de/paul-schrader) |
| Paul Vecchiali | Affiliated | 675 | 13633 | [paul-vecchiali](https://www.lacinetek.com/fr/la-liste-de/paul-vecchiali) |
| Paul Verhoeven | Affiliated | 575 | 5693 | [paul-verhoeven](https://www.lacinetek.com/fr/la-liste-de/paul-verhoeven) |
| Payal Kapadia | Affiliated | 2996 | 20675 | [payal-kapadia](https://www.lacinetek.com/fr/la-liste-de/payal-kapadia) |
| Pedro Costa | Affiliated | 1580 | 8900 | [pedro-costa](https://www.lacinetek.com/fr/la-liste-de/pedro-costa) |
| Pete Docter | Affiliated | 1269 | 14865 | [pete-docter](https://www.lacinetek.com/fr/la-liste-de/pete-docter) |
| Peter Handke | Affiliated | 2463 | 9793 | [peter-handke](https://www.lacinetek.com/fr/la-liste-de/peter-handke) |
| Philippe Garrel | Affiliated | 1808 | 3677 | [philippe-garrel](https://www.lacinetek.com/fr/la-liste-de/philippe-garrel) |
| Philippe Le Guay | Affiliated | 3393 | 20023 | [philippe-le-guay](https://www.lacinetek.com/fr/la-liste-de/philippe-le-guay) |
| Pierre Salvadori | Affiliated | 537 | 2636 | [pierre-salvadori](https://www.lacinetek.com/fr/la-liste-de/pierre-salvadori) |
| Radu Jude | Affiliated | 1233 | 16181 | [radu-jude](https://www.lacinetek.com/fr/la-liste-de/radu-jude) |
| Raymond Depardon | Affiliated | 534 | 3239 | [raymond-depardon](https://www.lacinetek.com/fr/la-liste-de/raymond-depardon) |
| Rebecca Zlotowski | Affiliated | 2009 | 18940 | [rebecca-zlotowski](https://www.lacinetek.com/fr/la-liste-de/rebecca-zlotowski) |
| Riad Sattouf | Affiliated | 583 | 12786 | [riad-sattouf-93](https://www.lacinetek.com/fr/la-liste-de/riad-sattouf-93) |
| Robert Guédiguian | Affiliated | 568 | 11031 | [robert-guediguian-49](https://www.lacinetek.com/fr/la-liste-de/robert-guediguian-49) |
| Robin Campillo | Affiliated | 557 | 10275 | [robin-campillo](https://www.lacinetek.com/fr/la-liste-de/robin-campillo) |
| Ryūsuke Hamaguchi | Affiliated | 2794 | 19779 | [ryusuke-hamaguchi](https://www.lacinetek.com/fr/la-liste-de/ryusuke-hamaguchi) |
| Saeed Roustaee | Affiliated | 1931 | 18522 | [saeed-roustaee](https://www.lacinetek.com/fr/la-liste-de/saeed-roustaee) |
| Sean Baker | Affiliated | 3210 | 21064 | [sean-baker](https://www.lacinetek.com/fr/la-liste-de/sean-baker) |
| Sébastien Lifshitz | Affiliated | 3722 | 22547 | [sebastien-lifshitz](https://www.lacinetek.com/fr/la-liste-de/sebastien-lifshitz) |
| Serge Bromberg | Affiliated | 1638 | 14352 | [serge-bromberg](https://www.lacinetek.com/fr/la-liste-de/serge-bromberg) |
| Sophie Letourneur | Affiliated | 2467 | 19610 | [sophie-letourneur](https://www.lacinetek.com/fr/la-liste-de/sophie-letourneur) |
| Stanley Kubrick | Archival | 1834 | 5117 | [stanley-kubrick-fdsv](https://www.lacinetek.com/fr/la-liste-de/stanley-kubrick-fdsv) |
| Thomas Arslan | Affiliated | 718 | 14881 | [thomas-arslan](https://www.lacinetek.com/fr/la-liste-de/thomas-arslan) |
| Thomas Cailley | Affiliated | 3360 | 21959 | [thomas-cailley](https://www.lacinetek.com/fr/la-liste-de/thomas-cailley) |
| Todd Haynes | Affiliated | 560 | 14099 | [todd-haynes-75](https://www.lacinetek.com/fr/la-liste-de/todd-haynes-75) |
| Valérie Donzelli | Affiliated | 3303 | 21946 | [valerie-donzelli](https://www.lacinetek.com/fr/la-liste-de/valerie-donzelli) |
| Valérie Lemercier | Affiliated | 3120 | 21602 | [valerie-lemercier-](https://www.lacinetek.com/fr/la-liste-de/valerie-lemercier-) |
| William Friedkin | Affiliated | 546 | 5030 | [william-friedkin](https://www.lacinetek.com/fr/la-liste-de/william-friedkin) |
| Wim Wenders | Affiliated | 562 | 3115 | [wim-wenders-22](https://www.lacinetek.com/fr/la-liste-de/wim-wenders-22) |
| Xavier Beauvois | Affiliated | 2171 | 13584 | [xavier-beauvois](https://www.lacinetek.com/fr/la-liste-de/xavier-beauvois) |
| Xavier Dolan | Affiliated | 2224 | 18348 | [xavier-dolan](https://www.lacinetek.com/fr/la-liste-de/xavier-dolan) |
| Yann Gonzalez | Affiliated | 570 | 11162 | [yann-gonzalez](https://www.lacinetek.com/fr/la-liste-de/yann-gonzalez) |
| Yolande Zauberman | Affiliated | 3058 | 17050 | [yolande-zauberman](https://www.lacinetek.com/fr/la-liste-de/yolande-zauberman) |

## Implementation gates

The first full-data release should fail instead of silently shrinking when any of these conditions is true:

- fewer than 158 roster records are fetched without a reviewed source change;
- a list ID, director ID, or canonical French slug is duplicated;
- a profile response does not match the requested list ID and slug;
- a named secondary list segment is flattened without its label;
- source positions are lost or treated as preference ranks;
- a film membership disappears merely because the product record is unavailable;
- Claire Simon or Valérie Donzelli is made selectable despite having no current selections;
- the random action can choose an empty profile;
- a product record is invented for IDs 2883 or 2888;
- the app needs a live LaCinetek call in order to render search, random selection, a biography, or a person's picks.

The final generated catalogue should report its profile count, selectable-profile count, selection count, unique mapped-movie count, unresolved count, and the three checksums above.
That makes "full list" measurable and prevents another four-film preview from being mistaken for the finished feature.

#!/usr/bin/env node

import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { gunzipSync } from "node:zlib";
import path from "node:path";
import process from "node:process";

const DEFAULT_SOURCE_URL = "https://www.lacinetek.com/fr-en/director-list/joon-ho-bong";
const LACINETEK_FILMS_URL = "https://www.lacinetek.com/fetch-films";
const KINOW_GRAPHQL_URL = "https://platform-257.kinow.io/graphql";
const PRODUCT_QUERY = `
  query FetchProductsByIds($ids: [ID!]) {
    cms {
      products(perPage: 50 includeIds: $ids query: "type:TVOD", sort: {field: "position", order: Asc}) {
        items {
          id
          name
          linkRewrite
          metadata { name value }
          images { source type }
          extension {
            ... on ProductTVOD {
              directors { items { director { name } roles } }
            }
          }
        }
      }
    }
  }
`;

function argumentValue(name, fallback) {
  const index = process.argv.indexOf(name);
  return index === -1 ? fallback : process.argv[index + 1];
}

const repoRoot = process.cwd();
const sourceUrl = argumentValue("--source-url", DEFAULT_SOURCE_URL);
const outputPath = path.resolve(repoRoot, argumentValue(
  "--output",
  "apps/web/app/taste-lens/data/lacinetek-catalogue.generated.json",
));
const rosterOutputPath = path.resolve(repoRoot, argumentValue(
  "--roster-output",
  "apps/web/app/taste-lens/lacinetek-roster.generated.json",
));
const movieLensArchivePath = path.resolve(repoRoot, argumentValue(
  "--movielens-archive",
  ".tools/datasets/movielens/ml-32m.zip",
));
const runtimeCataloguePath = path.resolve(repoRoot, argumentValue(
  "--runtime-catalogue",
  "apps/api/runtime/models/movielens-tmdb-catalog-v1.json.gz",
));
const envPath = path.resolve(repoRoot, argumentValue("--env-file", ".env"));
const checkedOn = argumentValue("--checked-on", new Date().toISOString().slice(0, 10));
const concurrency = Number.parseInt(argumentValue("--concurrency", "4"), 10);

function slugify(value) {
  return value
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function decodeHtml(value) {
  const named = {
    amp: "&",
    apos: "'",
    gt: ">",
    hellip: "…",
    laquo: "«",
    ldquo: "“",
    lsquo: "‘",
    nbsp: " ",
    quot: '"',
    raquo: "»",
    rdquo: "”",
    rsquo: "’",
  };
  return value
    .replace(/&#x([0-9a-f]+);/gi, (_, digits) => String.fromCodePoint(Number.parseInt(digits, 16)))
    .replace(/&#([0-9]+);/g, (_, digits) => String.fromCodePoint(Number.parseInt(digits, 10)))
    .replace(/&([a-z]+);/gi, (match, name) => named[name.toLowerCase()] ?? match);
}

function stripHtml(value) {
  return decodeHtml(value.replace(/<[^>]+>/g, " ")).replace(/\s+/g, " ").trim();
}

function normalizedName(value) {
  return slugify(value).replace(/-/g, " ");
}

function classifySourceList(value) {
  const normalized = normalizedName(value);
  if (normalized.includes("formative")) return "formative";
  if (normalized.includes("alternative")) return "alternative";
  return "published";
}

function uniquePresent(values) {
  return values.filter((value, index) => value && values.indexOf(value) === index);
}

function chunkValues(values, size) {
  const chunks = [];
  for (let offset = 0; offset < values.length; offset += size) {
    chunks.push(values.slice(offset, offset + size));
  }
  return chunks;
}

function bioFilmTitles(html) {
  const linked = [...html.matchAll(/<a\b[^>]*href=["'][^"']*\/film\/[^"']*["'][^>]*>([\s\S]*?)<\/a>/gi)]
    .map((match) => stripHtml(match[1]));
  const emphasized = [...html.matchAll(/<em\b[^>]*>([\s\S]*?)<\/em>/gi)]
    .map((match) => stripHtml(match[1]));
  const candidates = uniquePresent([...linked, ...emphasized])
    .filter((title) => title.length > 1 && title.length < 80)
    .filter((title) => !/^(cannes|venice|berlin|academy|festival)$/i.test(title));
  return candidates.slice(-3);
}

function naturalList(items) {
  if (items.length === 0) return "";
  if (items.length === 1) return items[0];
  if (items.length === 2) return `${items[0]} and ${items[1]}`;
  return `${items.slice(0, -1).join(", ")}, and ${items.at(-1)}`;
}

function fallbackDescription(director, knownForTitles, roleLabel) {
  if (knownForTitles.length > 0) {
    const titles = naturalList(knownForTitles);
    return `${roleLabel} known for ${titles}${/[.!?…]$/.test(titles) ? "" : "."}`;
  }
  const firstSentence = stripHtml(director.description ?? "").split(/(?<=[.!?])\s+/)[0] ?? "";
  return firstSentence || "Filmmaker with a published LaCinetek list.";
}

async function fetchWithRetry(url, options = {}, attempt = 1) {
  const response = await fetch(url, options);
  if (response.ok) return response;
  if (attempt >= 4) throw new Error(`${response.status} ${response.statusText} for ${url}`);
  await new Promise((resolve) => setTimeout(resolve, 300 * 2 ** attempt));
  return fetchWithRetry(url, options, attempt + 1);
}

function nextDataFromHtml(html, url) {
  const match = html.match(/<script id="__NEXT_DATA__" type="application\/json">([\s\S]*?)<\/script>/);
  if (!match) throw new Error(`No __NEXT_DATA__ payload found at ${url}`);
  return JSON.parse(match[1]);
}

async function fetchProfilePage(entry) {
  const url = `https://www.lacinetek.com/fr-en/director-list/${entry.linkRewrite}`;
  const html = await (await fetchWithRetry(url)).text();
  const list = nextDataFromHtml(html, url)?.props?.pageProps?.list;
  if (!list?.director || !Array.isArray(list.products)) {
    throw new Error(`Incomplete list payload for ${entry.name} at ${url}`);
  }
  return { entry, list, url };
}

async function mapLimit(items, limit, mapper) {
  const results = new Array(items.length);
  let nextIndex = 0;
  async function worker() {
    while (nextIndex < items.length) {
      const index = nextIndex;
      nextIndex += 1;
      results[index] = await mapper(items[index], index);
    }
  }
  await Promise.all(Array.from({ length: Math.min(limit, items.length) }, worker));
  return results;
}

async function fetchKinowProducts(ids) {
  const chunks = chunkValues(ids, 50);
  const responses = await mapLimit(chunks, 2, async (chunk) => {
    const response = await fetchWithRetry(KINOW_GRAPHQL_URL, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        origin: "https://www.lacinetek.com",
        referer: "https://www.lacinetek.com/",
      },
      body: JSON.stringify({ operationName: "FetchProductsByIds", variables: { ids: chunk }, query: PRODUCT_QUERY }),
    });
    const payload = await response.json();
    if (payload.errors?.length) throw new Error(`Kinow GraphQL error: ${JSON.stringify(payload.errors)}`);
    return payload?.data?.cms?.products?.items ?? [];
  });
  const byId = new Map(responses.flat().map((item) => [String(item.id), item]));
  return ids.map((id) => byId.get(String(id))).filter(Boolean);
}

async function fetchProducts(ids) {
  const chunks = chunkValues(ids, 40);
  const firstPartyResponses = await mapLimit(chunks, 2, async (chunk) => {
    const encodedIds = encodeURIComponent(JSON.stringify(chunk));
    const response = await fetchWithRetry(`${LACINETEK_FILMS_URL}/${encodedIds}`, {
      headers: { country: "FR" },
    });
    return response.json();
  });
  const firstPartyProducts = firstPartyResponses.flat();
  const kinowProducts = await fetchKinowProducts(ids);
  const kinowById = new Map(kinowProducts.map((product) => [String(product.id), product]));
  return firstPartyProducts.map((product) => {
    const kinow = kinowById.get(String(product.id));
    return kinow ? { ...product, metadata: kinow.metadata, extension: kinow.extension } : product;
  });
}

function metadataValue(product, names) {
  const normalized = new Set(names.map(normalizedName));
  const row = product.metadata?.find((item) => normalized.has(normalizedName(item.name ?? "")));
  return row?.value?.trim() || null;
}

function directorNames(product) {
  if (typeof product.director === "string" && product.director.trim()) {
    return [product.director.trim()];
  }
  const people = product.extension?.directors?.items ?? [];
  return uniquePresent(people
    .filter((item) => (item.roles ?? []).some((role) => normalizedName(role).includes("realisateur")))
    .map((item) => item.director?.name?.trim())
    .filter(Boolean));
}

function coverFor(product) {
  const images = product.images ?? [];
  return images.find((image) => image.type === "cover_large")?.source
    ?? images.find((image) => image.type === "photogramme_large")?.source
    ?? null;
}

function parseMovieLensLinks(archivePath) {
  const csv = execFileSync("unzip", ["-p", archivePath, "ml-32m/links.csv"], {
    encoding: "utf8",
    maxBuffer: 64 * 1024 * 1024,
  });
  const imdbToTmdb = new Map();
  for (const line of csv.trim().split("\n").slice(1)) {
    const [, imdbId, tmdbId] = line.replace(/\r$/, "").split(",");
    if (imdbId && tmdbId) imdbToTmdb.set(`tt${imdbId}`, tmdbId);
  }
  return imdbToTmdb;
}

function normalizeTitle(value) {
  return value
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/\(\d{4}\)\s*$/, "")
    .replace(/\b(the|a|an|le|la|les|un|une|des|de|l)\b/g, " ")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

async function loadRuntimeTitleMap(cataloguePath) {
  const compressed = await readFile(cataloguePath);
  const artifact = JSON.parse(gunzipSync(compressed).toString("utf8"));
  const titleYearToIds = new Map();
  for (const entry of artifact.entries ?? []) {
    const key = `${normalizeTitle(entry.title)}|${entry.release_year ?? ""}`;
    const ids = titleYearToIds.get(key) ?? [];
    ids.push(String(entry.source_movie_id).replace(/^tmdb:/, ""));
    titleYearToIds.set(key, ids);
  }
  return titleYearToIds;
}

function mappedTmdbId(product, imdbToTmdb, titleYearToIds) {
  const imdbId = metadataValue(product, ["imdb"]);
  if (imdbId && imdbToTmdb.has(imdbId)) return imdbToTmdb.get(imdbId);
  const releaseYear = product.year ?? metadataValue(product, ["année", "year"]);
  const possibleTitles = uniquePresent([
    product.name,
    product.original_title,
    metadataValue(product, ["nom original", "original title"]),
  ].filter(Boolean));
  for (const title of possibleTitles) {
    const ids = titleYearToIds.get(`${normalizeTitle(title)}|${releaseYear ?? ""}`) ?? [];
    if (ids.length === 1) return ids[0];
  }
  return null;
}

async function readEnv(filePath) {
  try {
    const text = await readFile(filePath, "utf8");
    return Object.fromEntries(text.split(/\r?\n/).flatMap((line) => {
      const match = line.match(/^([A-Z0-9_]+)=(.*)$/);
      if (!match) return [];
      return [[match[1], match[2].trim().replace(/^['"]|['"]$/g, "")]];
    }));
  } catch {
    return {};
  }
}

async function tmdbPersonContext(name, credentials) {
  if (!credentials.TMDB_READ_ACCESS_TOKEN && !credentials.TMDB_API_KEY) {
    return { roleLabel: "Filmmaker", titles: [] };
  }
  const url = new URL("https://api.themoviedb.org/3/search/person");
  url.searchParams.set("query", name);
  url.searchParams.set("include_adult", "false");
  url.searchParams.set("language", "en-US");
  if (credentials.TMDB_API_KEY) url.searchParams.set("api_key", credentials.TMDB_API_KEY);
  const headers = credentials.TMDB_READ_ACCESS_TOKEN
    ? { authorization: `Bearer ${credentials.TMDB_READ_ACCESS_TOKEN}` }
    : {};
  const response = await fetchWithRetry(url, { headers });
  const payload = await response.json();
  const exactName = normalizedName(name);
  const candidates = payload.results ?? [];
  const person = candidates.find((candidate) =>
    normalizedName(candidate.name ?? "") === exactName && candidate.known_for_department === "Directing"
  ) ?? candidates.find((candidate) => candidate.known_for_department === "Directing")
    ?? candidates.find((candidate) => normalizedName(candidate.name ?? "") === exactName);
  if (!person?.id) return { roleLabel: "Filmmaker", titles: [] };

  const creditsUrl = new URL(`https://api.themoviedb.org/3/person/${person.id}/movie_credits`);
  creditsUrl.searchParams.set("language", "en-US");
  if (credentials.TMDB_API_KEY) creditsUrl.searchParams.set("api_key", credentials.TMDB_API_KEY);
  const creditsResponse = await fetchWithRetry(creditsUrl, { headers });
  const credits = await creditsResponse.json();
  const directed = (credits.crew ?? [])
    .filter((credit) => credit.job === "Director" && (credit.title || credit.original_title));
  const directedIds = new Set(directed.map((credit) => credit.id));
  const knownDirected = (person.known_for ?? [])
    .filter((credit) => credit.media_type === "movie" && directedIds.has(credit.id));
  const recognizableDirected = [...directed].sort((left, right) =>
    (right.vote_count ?? 0) - (left.vote_count ?? 0) ||
    (right.popularity ?? 0) - (left.popularity ?? 0)
  );
  const directedTitles = uniquePresent([...knownDirected, ...recognizableDirected]
    .map((credit) => credit.title ?? credit.original_title)
    .filter(Boolean));
  if (directedTitles.length > 0) {
    return { roleLabel: "Director", titles: directedTitles.slice(0, 3) };
  }

  const knownMovieTitles = uniquePresent((person.known_for ?? [])
    .filter((credit) => credit.media_type === "movie")
    .map((credit) => credit.title ?? credit.original_title)
    .filter(Boolean));
  return { roleLabel: "Filmmaker", titles: knownMovieTitles.slice(0, 3) };
}

async function main() {
  const sourceHtml = await (await fetchWithRetry(sourceUrl)).text();
  const sourcePayload = nextDataFromHtml(sourceHtml, sourceUrl);
  const listsDirectory = sourcePayload?.props?.lists?.en;
  const roster = [
    ...(listsDirectory?.lists ?? []),
    ...(listsDirectory?.lifeLists ?? []),
  ];
  if (!Array.isArray(roster) || roster.length < 100) {
    throw new Error(`Expected the full LaCinetek roster, found ${roster.length} entries`);
  }

  console.error(`Fetching ${roster.length} LaCinetek profiles...`);
  const profiles = await mapLimit(roster, concurrency, fetchProfilePage);
  const imdbToTmdb = parseMovieLensLinks(movieLensArchivePath);
  const titleYearToIds = await loadRuntimeTitleMap(runtimeCataloguePath);
  const credentials = { ...(await readEnv(envPath)), ...process.env };

  let processed = 0;
  const curators = await mapLimit(profiles, concurrency, async ({ entry, list, url }) => {
    const displayName = (list.director.name?.trim() || entry.name.trim())
      .replace(/\s*\|\s*/g, " ")
      .replace(/\s+/g, " ");
    const selectionReferences = [
      ...list.products.map((productId, sourcePosition) => ({
        productId: String(productId),
        sourceListName: list.name?.trim() || entry.name.trim(),
        sourceListKind: "published",
        sourcePosition,
      })),
      ...(list.otherLists ?? []).flatMap((sourceList) =>
        (sourceList.products?.items ?? []).map((item, sourcePosition) => ({
          productId: String(item.id),
          sourceListName: sourceList.name?.trim() || "Published list",
          sourceListKind: classifySourceList(sourceList.name ?? ""),
          sourcePosition,
        }))
      ),
    ];
    const sourceProductIds = uniquePresent(selectionReferences.map((reference) => reference.productId));
    const products = await fetchProducts(sourceProductIds);
    const productsById = new Map(products.map((product) => [String(product.id), product]));
    const unresolvedSourceEntries = selectionReferences
      .filter(({ productId }) => !productsById.has(productId))
      .map(({ productId, sourceListName, sourceListKind, sourcePosition }) => ({
        sourceMovieId: `lacinetek:${productId}`,
        sourceListName,
        sourceListKind,
        sourcePosition,
        reason: "source-product-unavailable",
      }));
    const selections = selectionReferences.flatMap(({ productId, sourceListName, sourceListKind, sourcePosition }) => {
      const product = productsById.get(productId);
      if (!product) return [];
      const releaseYear = Number.parseInt(product.year ?? metadataValue(product, ["année", "year"]) ?? "", 10);
      const imdbId = metadataValue(product, ["imdb"]);
      const tmdbId = mappedTmdbId(product, imdbToTmdb, titleYearToIds);
      return [{
        movieId: tmdbId ? `tmdb:${tmdbId}` : null,
        sourceMovieId: `lacinetek:${productId}`,
        sourceMovieUrl: `https://www.lacinetek.com/fr-en/film/${product.linkRewrite}`,
        sourceListName,
        sourceListKind,
        sourcePosition,
        title: product.name.trim(),
        releaseYear: Number.isFinite(releaseYear) ? releaseYear : null,
        director: directorNames(product).join(", ") || "Director unavailable",
        imageUrl: coverFor(product),
        imdbId,
      }];
    });

    const tmdbContext = await tmdbPersonContext(displayName, credentials);
    let knownForTitles = tmdbContext.titles;
    if (knownForTitles.length < 2) knownForTitles = bioFilmTitles(list.director.description ?? "");
    const portraitUrl = list.director.images?.find((image) => image.type === "avatar_large")?.source
      ?? entry.director?.images?.find((image) => image.type === "avatar_large")?.source
      ?? null;
    const sourceId = `source:lacinetek-${slugify(displayName)}`;
    const curatorId = `curator:${slugify(displayName)}`;
    processed += 1;
    if (processed % 10 === 0 || processed === roster.length) console.error(`Processed ${processed}/${roster.length}`);
    return {
      id: curatorId,
      displayName,
      knownForTitles,
      sourceDescription: fallbackDescription(list.director, knownForTitles, tmdbContext.roleLabel),
      portrait: portraitUrl ? {
        imageUrl: portraitUrl,
        sourceUrl: url,
        author: "LaCinetek",
        license: "Source profile",
        attribution: `Profile image from ${displayName}'s LaCinetek page.`,
      } : null,
      source: {
        id: sourceId,
        publisher: "LaCinetek",
        sourceLabel: `${displayName}'s LaCinetek list`,
        sourceUrl: url,
        checkedOn,
        permissionStatus: "permission-required",
        selectionSignal: "formative",
        rankSemantics: "source-order-unknown",
        reportedDepth: {
          kind: "exact",
          count: selectionReferences.length,
          label: unresolvedSourceEntries.length === 0
            ? `${selections.length} published picks`
            : `${selections.length} available picks from ${selectionReferences.length} source entries`,
        },
        privateHouseholdResearch: {
          scope: "private-household-research",
          productUse: "not-cleared",
          note: "Stored locally for the owner's private, noncommercial household use.",
        },
      },
      unresolvedSourceEntries,
      selections,
    };
  });

  curators.sort((left, right) => left.displayName.localeCompare(right.displayName, "en"));
  const selectionCount = curators.reduce((sum, curator) => sum + curator.selections.length, 0);
  const mappedSelectionCount = curators.reduce(
    (sum, curator) => sum + curator.selections.filter((selection) => selection.movieId).length,
    0,
  );
  const sourceEntryCount = curators.reduce(
    (sum, curator) => sum + curator.source.reportedDepth.count,
    0,
  );
  const missingProductCount = curators.reduce(
    (sum, curator) => sum + curator.unresolvedSourceEntries.length,
    0,
  );
  const document = {
    schemaVersion: 1,
    generatedAt: new Date().toISOString(),
    checkedOn,
    source: {
      publisher: "LaCinetek",
      rosterUrl: sourceUrl,
      productEndpoint: KINOW_GRAPHQL_URL,
      firstPartyFilmEndpoint: LACINETEK_FILMS_URL,
    },
    stats: {
      sourceRosterCount: roster.length,
      includedCuratorCount: curators.length,
      activeCuratorCount: curators.filter((curator) => curator.selections.length > 0).length,
      sourceEntryCount,
      selectionCount,
      missingProductCount,
      mappedSelectionCount,
      unmappedSelectionCount: selectionCount - mappedSelectionCount,
      curatorsWithMappedSelections: curators.filter((curator) =>
        curator.selections.some((selection) => selection.movieId)
      ).length,
    },
    curators,
  };
  const canonical = `${JSON.stringify(document)}\n`;
  document.sha256 = createHash("sha256").update(canonical).digest("hex");
  await mkdir(path.dirname(outputPath), { recursive: true });
  await mkdir(path.dirname(rosterOutputPath), { recursive: true });
  await writeFile(outputPath, `${JSON.stringify(document, null, 2)}\n`);
  const rosterDocument = {
    schemaVersion: document.schemaVersion,
    generatedAt: document.generatedAt,
    checkedOn: document.checkedOn,
    source: document.source,
    sourceCatalogueSha256: document.sha256,
    stats: document.stats,
    curators: curators.map((curator) => ({
      id: curator.id,
      displayName: curator.displayName,
      knownForTitles: curator.knownForTitles,
      sourceDescription: curator.sourceDescription,
      portrait: curator.portrait,
      source: curator.source,
      publishedSelectionCount: curator.selections.length,
      mappedSelectionCount: curator.selections.filter((selection) => selection.movieId).length,
      mappedMovieIds: uniquePresent(curator.selections.map((selection) => selection.movieId).filter(Boolean)),
      sourceListNames: uniquePresent(curator.selections.map((selection) => selection.sourceListName)),
    })),
  };
  await writeFile(rosterOutputPath, `${JSON.stringify(rosterDocument, null, 2)}\n`);
  console.error(JSON.stringify({ outputPath, rosterOutputPath, ...document.stats, sha256: document.sha256 }, null, 2));
}

await main();

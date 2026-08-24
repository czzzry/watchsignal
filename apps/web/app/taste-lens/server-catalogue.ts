import catalogue from "./data/lacinetek-catalogue.generated.json" with { type: "json" };

/** Server-only lookup used by the private catalogue route. */
export function tasteLensCatalogueForRouteParameter(curatorId: string) {
  let normalizedCuratorId = curatorId;
  try {
    normalizedCuratorId = decodeURIComponent(curatorId);
  } catch {
    return null;
  }
  return catalogue.curators.find((entry) => entry.id === normalizedCuratorId) ?? null;
}

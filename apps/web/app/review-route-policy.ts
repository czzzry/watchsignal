const reviewOnlyRoutePrefixes = ["/prototype", "/showcase"] as const;
const reviewOnlyExactRoutes = new Set(["/redesign-gauntlet-status.json"]);

export function isReviewOnlyRoute(pathname: string): boolean {
  return (
    reviewOnlyExactRoutes.has(pathname) ||
    reviewOnlyRoutePrefixes.some(
      (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
    )
  );
}

export function shouldHideReviewOnlyRoute(
  pathname: string,
  nodeEnv: string | undefined,
): boolean {
  return nodeEnv === "production" && isReviewOnlyRoute(pathname);
}

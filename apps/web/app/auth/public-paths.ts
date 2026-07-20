export function isPublicAppPath(pathname: string): boolean {
  return (
    pathname === "/login" ||
    pathname === "/credits" ||
    pathname === "/showcase" ||
    pathname.startsWith("/showcase/") ||
    pathname === "/manifest.webmanifest" ||
    pathname.startsWith("/api/auth/") ||
    pathname.startsWith("/icons/") ||
    pathname.startsWith("/_next/")
  );
}

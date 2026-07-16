import { NextRequest, NextResponse } from "next/server";
import {
  SESSION_COOKIE_NAME,
  verifySessionToken,
} from "./app/auth/session";

export async function proxy(request: NextRequest): Promise<NextResponse> {
  const password = process.env.HOUSEHOLD_ACCESS_PASSWORD;
  const sessionSecret = process.env.HOUSEHOLD_SESSION_SECRET;
  const hosted = Boolean(process.env.VERCEL_ENV);

  if (!password || !sessionSecret) {
    if (hosted) {
      return new NextResponse("WatchSignal household access is not configured.", {
        status: 503,
      });
    }
    return NextResponse.next();
  }

  if (isPublicPath(request.nextUrl.pathname)) {
    return NextResponse.next();
  }

  const token = request.cookies.get(SESSION_COOKIE_NAME)?.value;
  if (await verifySessionToken(token, sessionSecret)) {
    return NextResponse.next();
  }

  if (request.nextUrl.pathname.startsWith("/api/")) {
    return NextResponse.json({ detail: "Household sign-in required." }, { status: 401 });
  }

  const loginUrl = request.nextUrl.clone();
  loginUrl.pathname = "/login";
  loginUrl.search = "";
  return NextResponse.redirect(loginUrl);
}

function isPublicPath(pathname: string): boolean {
  return (
    pathname === "/login" ||
    pathname === "/manifest.webmanifest" ||
    pathname.startsWith("/api/auth/") ||
    pathname.startsWith("/icons/") ||
    pathname.startsWith("/_next/")
  );
}

export const config = {
  matcher: ["/((?!.*\\..*).*)", "/"],
};

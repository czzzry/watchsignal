import { timingSafeEqual } from "node:crypto";
import { cookies } from "next/headers";
import {
  createSessionToken,
  SESSION_COOKIE_NAME,
  SESSION_LIFETIME_SECONDS,
} from "../../../auth/session";

export async function POST(request: Request): Promise<Response> {
  const configuredPassword = process.env.HOUSEHOLD_ACCESS_PASSWORD;
  const sessionSecret = process.env.HOUSEHOLD_SESSION_SECRET;
  if (!configuredPassword || !sessionSecret) {
    return Response.json(
      { detail: "Household access is not configured." },
      { status: 503 },
    );
  }

  const payload = (await request.json().catch(() => null)) as unknown;
  const password = readPassword(payload);
  if (!password || !matches(password, configuredPassword)) {
    return Response.json({ detail: "That passphrase is not correct." }, { status: 401 });
  }

  const token = await createSessionToken(sessionSecret);
  const cookieStore = await cookies();
  cookieStore.set(SESSION_COOKIE_NAME, token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: SESSION_LIFETIME_SECONDS,
  });
  return Response.json({ status: "ok" });
}

function readPassword(payload: unknown): string | null {
  if (
    typeof payload === "object" &&
    payload !== null &&
    "password" in payload &&
    typeof payload.password === "string"
  ) {
    return payload.password;
  }
  return null;
}

function matches(supplied: string, expected: string): boolean {
  const suppliedBytes = Buffer.from(supplied);
  const expectedBytes = Buffer.from(expected);
  return (
    suppliedBytes.length === expectedBytes.length &&
    timingSafeEqual(suppliedBytes, expectedBytes)
  );
}

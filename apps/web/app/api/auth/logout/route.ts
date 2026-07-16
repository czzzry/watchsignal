import { cookies } from "next/headers";
import { SESSION_COOKIE_NAME } from "../../../auth/session";

export async function POST(): Promise<Response> {
  const cookieStore = await cookies();
  cookieStore.delete(SESSION_COOKIE_NAME);
  return Response.json({ status: "ok" });
}

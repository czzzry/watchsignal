export async function GET(): Promise<Response> {
  return Response.json({
    build: process.env.VERCEL_GIT_COMMIT_SHA?.slice(0, 7) ?? "local",
    environment: process.env.VERCEL_ENV ?? "local",
  });
}

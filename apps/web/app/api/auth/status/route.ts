export async function GET(): Promise<Response> {
  return Response.json({ enabled: Boolean(process.env.HOUSEHOLD_ACCESS_PASSWORD) });
}

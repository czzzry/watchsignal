import { deleteBackendSession } from "../../session/backend";

export async function DELETE(
  request: Request,
  context: { params: Promise<{ sourceMovieId: string }> },
): Promise<Response> {
  const { sourceMovieId } = await context.params;
  const { search } = new URL(request.url);

  return deleteBackendSession(
    `/watchlist/${encodeURIComponent(sourceMovieId)}${search}`,
  );
}

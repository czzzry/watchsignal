import { NextResponse } from "next/server";

import catalogue from "../../../../taste-lens/data/lacinetek-catalogue.generated.json" with { type: "json" };

export async function GET(
  _request: Request,
  context: { params: Promise<{ curatorId: string }> },
) {
  const { curatorId } = await context.params;
  const curator = catalogue.curators.find((entry) => entry.id === curatorId);
  if (!curator || curator.selections.length === 0) {
    return NextResponse.json({ error: "Taste Lens catalogue not found." }, { status: 404 });
  }
  return NextResponse.json({
    curatorId: curator.id,
    displayName: curator.displayName,
    selections: curator.selections.map((selection) => ({
      movieId: selection.movieId,
      sourceMovieId: selection.sourceMovieId,
      sourceMovieUrl: selection.sourceMovieUrl,
      sourceListName: selection.sourceListName,
      sourcePosition: selection.sourcePosition,
      title: selection.title,
      releaseYear: selection.releaseYear,
      director: selection.director,
      imageUrl: selection.imageUrl,
    })),
  }, {
    headers: { "Cache-Control": "private, max-age=86400" },
  });
}

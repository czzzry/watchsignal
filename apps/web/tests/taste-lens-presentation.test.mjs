import assert from "node:assert/strict";
import test from "node:test";

import {
  localSeedEligibilityFor,
  tasteLensLaunchRoster,
  tasteLensModeAvailability,
  tasteLensSourceById,
} from "../app/taste-lens/index.ts";
import { tasteLensProfilePresentation } from "../app/pass-the-phone/taste-lens-presentation-contract.ts";

test("Taste Lens presents clear actions with quiet, source-level attribution", () => {
  const curator = tasteLensLaunchRoster.find((profile) => profile.id === "curator:bong-joon-ho");
  assert.ok(curator);
  const source = tasteLensSourceById.get(curator.sourceIds[0]);
  assert.ok(source);

  const presentation = tasteLensProfilePresentation({
    curator,
    source,
    availability: tasteLensModeAvailability({
      curator,
      sources: tasteLensSourceById,
      eligibility: localSeedEligibilityFor(curator.id),
      usageScope: "local-personal-research-testing",
    }),
    personalResearchPreview: true,
  });

  assert.deepEqual(presentation.actions, [
    {
      mode: "inspiration",
      label: "Use as inspiration",
      detail: "Find movies connected to these picks and your taste.",
    },
    {
      mode: "browse",
      label: "See their picks",
      detail: "Skip matching and browse the source list.",
    },
  ]);
  assert.deepEqual(presentation.sourceCredit, {
    tone: "quiet",
    publisher: "BFI Sight and Sound",
    sourceUrl: "https://www.bfi.org.uk/sight-and-sound/greatest-films-all-time/all-voters/bong-joon-ho",
    checkedCountLabel: "4 picks checked",
    aboutLabel: "About this source",
    detail: "10 Directors' Poll selections. WatchSignal uses only the titles checked against the published list.",
  });

  const visibleCopy = JSON.stringify(presentation);
  assert.doesNotMatch(visibleCopy, /Attributed source|Personal research preview|No popularity fallback/);
  assert.equal("sourceMovieUrl" in presentation.sourceCredit, false);
});

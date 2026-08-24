import assert from "node:assert/strict";
import test from "node:test";

import {
  tasteLensEligibilityFor,
  tasteLensCuratorDirectory,
  tasteLensModeAvailability,
  tasteLensSourceById,
} from "../app/taste-lens/index.ts";
import { tasteLensProfilePresentation } from "../app/pass-the-phone/taste-lens-presentation-contract.ts";

test("Taste Lens presents clear actions with quiet, source-level attribution", () => {
  const curator = tasteLensCuratorDirectory.find((profile) => profile.id === "curator:bong-joon-ho");
  assert.ok(curator);
  const source = tasteLensSourceById.get(curator.sourceIds[0]);
  assert.ok(source);

  const presentation = tasteLensProfilePresentation({
    curator,
    source,
    availability: tasteLensModeAvailability({
      curator,
      sources: tasteLensSourceById,
      eligibility: tasteLensEligibilityFor(curator.id),
      usageScope: "private-household-research",
    }),
    privateHouseholdCatalogue: true,
  });

  assert.deepEqual(presentation.actions, [
    {
      mode: "inspiration",
      label: "Use as inspiration",
      detail: "Let their picks steer tonight's recommendations.",
    },
    {
      mode: "browse",
      label: "See their list",
      detail: "Skip matching and browse what they chose.",
    },
    {
      mode: "exact-list",
      label: "Pick from their list",
      detail: "Rank their published picks for your household.",
    },
  ]);
  assert.deepEqual(presentation.sourceCredit, {
    tone: "quiet",
    publisher: "LaCinetek",
    sourceUrl: "https://www.lacinetek.com/fr-en/director-list/joon-ho-bong",
    checkedCountLabel: "50 published picks",
  });

  const visibleCopy = JSON.stringify(presentation);
  assert.doesNotMatch(visibleCopy, /Attributed source|Personal research preview|No popularity fallback/);
  assert.equal("sourceMovieUrl" in presentation.sourceCredit, false);
});

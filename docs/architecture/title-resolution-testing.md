# Title Resolution Testing

Hybrid title resolution has two test paths.

Deterministic adapter tests use fixture-backed TMDb-shaped candidates and never call the network.
They prove that backend code can handle likely matches, typo fixtures, ambiguous matches, selected resolved candidates, and unresolved plain-text titles.

Live TMDb smoke tests are manual integration checks.
They prove that local credentials still work and that TMDb still returns the metadata shape the product expects.
They are intentionally separate from the normal test suite because credentials, network access, rate limits, and upstream data changes would make automated tests flaky.

The production adapter should keep the same domain boundary as the fixture resolver.
Application code should receive title candidates and title entries, not raw TMDb response payloads.

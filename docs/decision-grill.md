# Decision Grill

Use this document to pressure-test the current recommendation set before accepting any architecture.
It is grounded in the repository's current [decision register](decision-register.md) and architecture notes.
The goal is not to answer fast.
The goal is to help the founder accept, reject, or modify each recommendation deliberately.

## Product framing

- If this becomes more than a household mediator, what exact user problem are we solving that existing movie products do not already solve well?
- What would count as success in the first month: faster decisions, fewer debates, better picks, better data, or a stronger portfolio artifact?
- What feature idea would most tempt us into accidentally building a full movie app?

## Build vs buy

- If an existing product covered most of the need, what remaining gap would still justify building this project?
- Is the main value personal utility, product thinking practice, portfolio value, or recommender experimentation?
- What part of the system would feel wasteful to build ourselves if a stable external product already does it better?

## Interface platform

- Do both intended users actually want to interact through chat, or is that an implementation convenience?
- Which parts of the flow truly benefit from buttons, polls, or structured input rather than free text?
- If Telegram is the current recommendation, what evidence would justify choosing a different interface first?

## Movie data source

- What fields are truly required for the first useful version: genre, runtime, year, language, providers, popularity, synopsis, cast, or something else?
- Do we need one canonical source for metadata only, or also for watch history and streaming availability?
- What is the tolerance for occasional missing or inconsistent metadata if the source is otherwise easy to work with?

## Storage layer

- What needs to be directly inspectable and auditable from day one?
- How much concurrency, structure, and analytics do we realistically need in the first version?
- Are we optimizing first for learning speed and visibility, or for a storage layer that is already shaped for long-term growth?

## Recommendation method

- What would make a recommendation feel trustworthy to the household: transparency, novelty, accuracy, explainability, fairness, or surprise?
- Is the first goal to produce a trustworthy shortlist tonight, or to start building a more experimental recommender system?
- What level of algorithmic complexity would stop this from feeling inspectable and maintainable?

## Feedback mechanism

- What level of post-watch effort will each person reliably tolerate every time?
- What feedback format would still be used honestly when someone is tired, indifferent, or mildly disappointed?
- Are we optimizing for future modeling quality or for consistent participation?

## Couple consensus rule

- Is the product trying to maximize shared excitement, minimize regret, rotate fairness, or avoid conflict?
- Under what circumstances should one person be able to veto a title completely?
- If the same partner loses out three sessions in a row, what should the system do differently?

## LLM role

- What exact problem are we asking an LLM to solve that deterministic logic cannot solve well enough?
- Which parts of the system must remain fully explainable to the founder at all times?
- What failure would be unacceptable: a wrong filter, a hallucinated fact, an opaque ranking, or unreviewable cost growth?

## Privacy model

- What household information would feel invasive if it appeared in logs, screenshots, workflow exports, or a public repo by accident?
- What minimum private identifiers are actually required for the product to function?
- What public artifact could we share proudly without revealing anything private?

## n8n vs code boundary

- Which logic should remain visible in a workflow graph, and which logic deserves tests and a clearer code boundary?
- What would make the workflow feel like brittle spaghetti instead of orchestration?
- If a scoring rule changes often, where should that logic live so it stays understandable?

## Repo/public portfolio strategy

- If all personal data is removed, what is the strongest public story this repo should tell?
- What would an employer or reviewer learn from this repo if all real data is removed?
- If the repo stayed private forever, what would we still want documented well?

## Deployment model

- Are we optimizing first for low operations, privacy control, portability, or platform flexibility?
- What deployment option would we regret choosing if this stays a lightweight personal tool?
- What constraint would force us away from a boring managed starting point?

## External paid vendors

- What paid service would create real user value rather than simply making implementation more convenient?
- Where is free-tier fragility acceptable, and where would it become product risk?
- What vendor decision would be hardest to reverse later?

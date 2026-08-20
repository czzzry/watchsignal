# Product README Playbook

This playbook captures the reusable decisions from the WatchSignal README redesign so another product, including Threadwise, can reach the same quality bar without repeating the discovery work.

## The job of the page

A product README should answer four questions in order.

1. What is this?
2. Why would someone care?
3. What does using it feel like?
4. Why should the implementation be taken seriously?

Installation belongs after those answers unless the repository is primarily a library or command-line tool.

## Recommended order

1. Product name and one plain sentence.
2. One strong hero that shows the real product.
3. A short explanation of the user problem and the product's answer.
4. One visual sequence with no more than three or four moments.
5. The project's most distinctive technical or research proof.
6. The shortest reliable local start.
7. Stack, status, limits, and deeper documentation.

The opening should be understandable without reading captions inside an image.
The image should strengthen the explanation rather than carry it alone.

## Hero rules

- Use one flat composition instead of overlapping or cascading screens.
- Make one real product screen the visual anchor.
- Avoid a close crop of a face unless the product itself is about that person.
- Show real provider art when recognizable media appears.
- Keep the main subject readable at 1,000 pixels wide and still recognizable around 380 pixels wide.
- Use a dark asset that looks intentional in both GitHub light and dark themes.
- Keep words inside the image short because GitHub scales the entire asset on phones.
- Do not repeat the page title, tagline, and full product explanation inside the asset.

A practical default is a 2:1 image around 1,440 by 720 pixels with one product screen and a small amount of supporting copy.

## Screenshot storytelling

Use a sequence only when each frame answers a different question.

- Frame 1 shows the core action.
- Frame 2 shows the important transition or trust mechanism.
- Frame 3 shows the outcome.

Keep the movie, profile names, device size, interface version, and visual treatment consistent across the sequence.
Remove browser chrome, development badges, focus artifacts, test-only names, stale copy, and loading mismatches.
Prefer one composed storyboard over several large screenshots when the flow is short.

## Human copy rules

- State what the product does before explaining the architecture.
- Use the words a user would use, such as "Pass the phone," instead of internal mechanism names.
- Replace slogans with specific behavior.
- Avoid phrases such as "seamless," "powerful," "unlock," "delve," "not just," and "turns X into Y."
- Keep one idea per paragraph.
- Use short headings that describe the reader's question.
- Say when a claim is uncertain or incomplete.
- Do not describe every engineering choice as deliberate, robust, or production-grade.

## Research and machine-learning sections

A good research section explains the experiment, not only the model name.

Include:

1. The dataset and its scale.
2. What information the model was allowed to see.
3. What was held back.
4. How people or rows were split between fitting, tuning, and final evaluation.
5. The simple baselines that the learned models had to beat.
6. The metrics and safety checks.
7. The final result and uncertainty.
8. Why the selected model won.
9. What the result does not prove.

Connect each paper to one concrete decision.
Do not imply that a paper selected project-specific hyperparameters or validated project-specific results.
Separate technical foundations from sources that were explicitly cited during the original work.

One diagram should show the experimental flow.
A compact table can show the papers and what each influenced.
Long protocol details should link to a deeper document.

## GitHub rendering checks

Render the actual Markdown rather than judging a separate landing-page mockup.

Check:

- GitHub-like light and dark themes.
- Desktop around 1,000 to 1,280 pixels wide.
- Mobile around 390 to 430 pixels wide.
- Image loading and intrinsic dimensions.
- Heading rhythm and total page length.
- Table wrapping and horizontal overflow.
- Code-block width.
- Local links and image paths.
- Alt text that explains the information rather than the decoration.

The hero, story image, and evidence diagram should be reviewed as separate assets and again inside the rendered page.

## Independent quality gate

Use at least two independent reviews after the authoring pass.

One review should judge the page as a product reader.
The other should audit claims, sources, links, and repository truth.

For a blind visual comparison, label screenshots as candidates without identifying which one is the new work.
Compare against the chosen reference on hierarchy, clarity, pacing, credibility, and finish rather than pixel similarity.

Do not accept a page when any of these are true:

- The opening does not explain the product.
- The images use inconsistent or visibly fake states.
- The hero is a face crop, generic montage, or unreadable collage.
- Research claims cannot be traced to code, committed evidence, or primary sources.
- The README claims more than the product currently does.
- The page depends on a prototype that differs from the committed Markdown.

## Lightweight delivery loop

Use this five-stage status bar for future work.

1. Audit the existing README, product truth, and reusable assets.
2. Lock the narrative and source-backed claims.
3. Implement the Markdown and final imagery.
4. Render and refine the actual GitHub page.
5. Run independent visual and factual judging, then validate links and files.

Keep only one heavy browser or build task active at a time.
Stop temporary preview servers and browser bridges after the evidence is saved.

# Redesign Retro Notes

## Why this exists

This note captures a lesson from the first flagship-UI redesign push in Movie Night Mediator.
The goal is to help future design work choose the right rendering approach earlier, before time is spent forcing the wrong tool into the job.

## What was hard

The startup screen needed to feel like polished concept art translated into a real product.
That turned out to be harder than expected because the work mixed two different problems.

The first problem was normal product UI work.
That includes spacing, hierarchy, cards, buttons, labels, and mobile layout.

The second problem was hero-art direction.
That includes the luminous particle cloud, motion feel, signature atmosphere, and premium opening impression.

We treated too much of the second problem like it could be solved by iterating on CSS styling alone.
That created a long detour.

## Core lesson

For flagship surfaces, decide the rendering tier up front.

Do not start with, "Can we force this through CSS?"
Start with, "What kind of thing is this?"

If it is mostly layout and materials, CSS is usually right.
If it is art, motion, or a signature hero moment, CSS may only be the framing layer.

## Rendering options

### 1. CSS only

Use CSS when the problem is mostly:
- layout
- typography
- glass panels
- gradients
- glows
- standard transitions

Good for:
- cards
- buttons
- progress bars
- page composition

Bad for:
- complex organic hero shapes
- particle clouds
- bespoke motion graphics
- anything that needs to look like concept art

### 2. SVG

Use SVG when the problem is:
- a custom static illustration
- a logo-like shape
- an effect that must stay crisp at any size

Good for:
- icons
- decorative linework
- static hero shapes
- masked gradients

Bad for:
- dense natural-looking particle simulation unless carefully authored
- high-end motion unless paired with animation tooling

### 3. Lottie or Rive

Use Lottie or Rive when:
- the visual motion is known up front
- there is a designed asset to embed
- you want reliable playback without inventing the motion system yourself

Good for:
- hero loops
- branded intros
- decorative motion
- polished repeatable signature moments

Best when:
- the motion is asset-driven rather than simulation-driven

### 4. Canvas

Use canvas when:
- you want lightweight generative motion
- you need many particles
- the effect should feel alive without full 3D complexity

Good for:
- particle clouds
- flowing dots
- subtle simulation
- neon atmospheric hero art

Best when:
- the effect is dynamic and custom, but does not need full 3D scene tooling

### 5. WebGL or Three.js

Use WebGL or Three.js when:
- the hero is a major product moment
- depth, parallax, lighting, or volumetric behavior really matter
- the interaction should feel closer to motion art than UI decoration

Good for:
- premium hero visuals
- reactive particle systems
- camera-driven motion
- high-end cinematic surfaces

Tradeoff:
- more implementation complexity
- more performance and mobile QA burden

### 6. Raster or video asset

Use a raster asset or short loop when:
- the exact art direction matters more than simulation purity
- you already know the look you want
- the surface is mostly decorative

Good for:
- splash moments
- ambient hero art
- shipping faster when the look is fixed

Tradeoff:
- less flexible
- harder to adapt dynamically

## What we should do earlier next time

Before building a flagship screen, pause and classify the hero layer.

Ask:
- Is this layout-first or art-first?
- Does this need to feel alive?
- Does it need simulation, authored motion, or just a still image?
- Is the exact concept look more important than implementation purity?

Then pick a lane early.

## Practical rule of thumb

If the team says things like:
- "premium hero"
- "signature moment"
- "dynamic particle blob"
- "looks like concept art"
- "high-end startup scene"

then default away from CSS-only.

That is the signal to evaluate:
- SVG asset
- Lottie or Rive
- canvas
- or WebGL

## Recommended process for the next flagship surface

1. Lock the reference image and list what is actually essential.
2. Separate hero-art requirements from normal UI requirements.
3. Choose the rendering tier before styling the rest of the screen.
4. Build the hero proof first.
5. Only then integrate the surrounding UI.

## Plain-English summary

The main mistake was trying to solve a hero-art problem as if it were mostly a CSS polish problem.
For future premium surfaces, we should decide much earlier whether the work belongs in CSS, SVG, Lottie, canvas, WebGL, or a fixed asset.
That should save time, reduce churn, and produce results that stay closer to the intended concept.

---
name: WatchSignal
description: A cinematic decision tool for two people sharing one phone.
colors:
  night-950: "#050309"
  night-900: "#0A0610"
  night-850: "#100817"
  plum-800: "#1C1026"
  plum-700: "#2B183A"
  signal-400: "#B986FF"
  signal-300: "#D5BDFF"
  cyan-500: "#78E8F5"
  paper-50: "#FAF8FC"
  paper-100: "#F5F2F8"
  ink-900: "#1B1124"
  ink-700: "#554A5A"
  danger-400: "#FF8F9C"
  success-400: "#9EE0BD"
  warning-400: "#F4CA8B"
typography:
  display:
    fontFamily: '"New York", "Iowan Old Style", "Palatino Linotype", Baskerville, Georgia, serif'
    fontSize: "clamp(2.5rem, 11vw, 3.5rem)"
    fontWeight: 600
    lineHeight: 1.05
    letterSpacing: "-0.03em"
  headline:
    fontFamily: '"Avenir Next", "SF Pro Text", "Segoe UI Variable Text", "Segoe UI", system-ui, sans-serif'
    fontSize: "1.75rem"
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "-0.03em"
  title:
    fontFamily: '"Avenir Next", "SF Pro Text", "Segoe UI Variable Text", "Segoe UI", system-ui, sans-serif'
    fontSize: "1.25rem"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-0.015em"
  body:
    fontFamily: '"Avenir Next", "SF Pro Text", "Segoe UI Variable Text", "Segoe UI", system-ui, sans-serif'
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
  label:
    fontFamily: '"Avenir Next", "SF Pro Text", "Segoe UI Variable Text", "Segoe UI", system-ui, sans-serif'
    fontSize: "0.75rem"
    fontWeight: 700
    lineHeight: 1.35
    letterSpacing: "-0.015em"
rounded:
  sm: "8px"
  md: "12px"
  lg: "16px"
  pill: "999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  base: "16px"
  lg: "20px"
  xl: "24px"
  2xl: "32px"
  3xl: "40px"
  4xl: "48px"
components:
  button-primary:
    backgroundColor: "{colors.paper-50}"
    textColor: "{colors.ink-900}"
    rounded: "{rounded.md}"
    padding: "0 20px"
    height: "54px"
  button-secondary:
    backgroundColor: "{colors.night-850}"
    textColor: "{colors.paper-50}"
    rounded: "{rounded.md}"
    padding: "0 20px"
    height: "48px"
  button-icon:
    backgroundColor: "{colors.night-850}"
    textColor: "{colors.paper-50}"
    rounded: "{rounded.pill}"
    height: "44px"
    width: "44px"
  sheet-light:
    backgroundColor: "{colors.paper-100}"
    textColor: "{colors.ink-900}"
    rounded: "{rounded.lg}"
    padding: "16px"
  movie-card:
    backgroundColor: "{colors.plum-800}"
    textColor: "{colors.paper-50}"
    rounded: "{rounded.lg}"
    padding: "16px"
---

# Design System: WatchSignal

## 1. Overview

**Creative North Star: "The Private Screening Room"**

WatchSignal is a premium cinematic mobile product with a restrained nightlife signal running through it.
It should feel like two people have entered a focused private screening room where the product quietly does the difficult work and gives one movie the stage.
The experience moves between three related modes: backdrop-led cinema stages for reactions and results, calm matte utility surfaces for setup and supporting work, and short transition chambers for privacy, loading, and reveal moments.

The system rejects generic streaming-service chrome, gamer styling, decorative neon, flat prototype utility, and interface ornament that competes with the decision.
Real movie imagery or a deliberately authored WatchSignal object supplies atmosphere.
Controls remain familiar, readable, and stable underneath the cinematic presentation.

**Key Characteristics:**

- Phone-first and safe-area-aware, with a primary canvas of 390 by 844 pixels and support from 320 to 430 pixels wide.
- Near-black and plum surfaces with restrained violet and cyan signals.
- Real poster and backdrop art used as decision context rather than wallpaper.
- One dominant action per state, with secondary work progressively disclosed.
- Short state-driven motion at signature moments and stable reading surfaces everywhere else.
- Human language, honest errors, and no consumer-facing algorithm jargon.

## 2. Colors

The palette begins in near-black cinema darkness, uses plum for depth, and reserves violet and cyan for meaningful signals.

### Primary

- **Signal Violet** (`signal-400`): The main identity and selected-state signal for progress, scores, focus, and rare moments of emphasis.
- **Signal Lavender** (`signal-300`): A quieter companion for secondary signal text and supporting status.

### Secondary

- **Electric Cyan** (`cyan-500`): A restrained counter-signal for participant identity, focus, and selected supporting states.

### Tertiary

- **Danger Rose** (`danger-400`), **Success Mint** (`success-400`), and **Warning Amber** (`warning-400`): Semantic feedback only.
These colors never become decorative theme accents.

### Neutral

- **Cinema Black** (`night-950`): The main canvas and the deepest point in image scrims.
- **Night Black** (`night-900`) and **Raised Night** (`night-850`): Tonal depth for utility layers and transitions.
- **Deep Plum** (`plum-800`) and **Raised Plum** (`plum-700`): Intentional fallbacks, selected surfaces, and the brand's darker material character.
- **Projection White** (`paper-50`) and **Reading Sheet** (`paper-100`): Primary dark-mode text, actions, and pale detail sheets.
- **Dark Ink** (`ink-900`) and **Muted Ink** (`ink-700`): Text and controls on pale surfaces.

### Named Rules

**The Signal Rarity Rule.** Violet and cyan communicate identity, selection, progress, or recommendation strength and never exist as ambient decoration alone.

**The Honest Image Rule.** Essential text over dynamic artwork always receives a deterministic contrast scrim, while missing art receives the deliberate plum fallback rather than a broken image or fake poster.

## 3. Typography

**Display Font:** New York, with Iowan Old Style, Palatino Linotype, Baskerville, and Georgia fallbacks.

**Body Font:** Avenir Next, with SF Pro Text, Segoe UI, and system sans-serif fallbacks.

**Character:** The serif gives movie titles, handoffs, launch, and the final reveal a cinematic voice.
The sans-serif carries every control, label, explanation, and utility screen with familiar product clarity.

### Hierarchy

- **Display** (600, `display`, 1.05): Movie titles and major cinematic moments only, balanced and never tighter than minus 0.03 em.
- **Headline** (700, `headline`, 1.1): Primary utility-screen headings and decisive setup copy.
- **Title** (700, `title`, 1.2): Sheet titles, section headings, and meaningful component labels.
- **Body** (400, `body`, 1.5): Explanations and instructions, capped at roughly 65 characters where a long reading measure exists.
- **Label** (700, `label`, 1.35): Controls, compact metadata, and status language, never below 12 pixels in production.

### Named Rules

**The Movie Owns the Serif Rule.** Serif type belongs to titles and signature cinematic moments, never buttons, forms, navigation, or diagnostic text.

**The Twelve Pixel Floor.** Production body, metadata, and control text never render below 12 pixels.

## 4. Elevation

WatchSignal uses tonal layering first and shadows only when a surface must visibly separate from movie art or another interaction layer.
Cinema stages rely on scrims and image depth, utility views rely on matte surface contrast, and dialogs or sheets use one restrained structural shadow.

### Shadow Vocabulary

- **Compact Lift** (`0 4px 16px rgba(0, 0, 0, 0.22)`): Toasts, small floating feedback, and compact overlays.
- **Sheet Lift** (`0 20px 48px rgba(0, 0, 0, 0.38)`): Dialogs and bottom sheets that must separate from the stage below.
- **Poster Anchor** (`0 8px 8px rgba(0, 0, 0, 0.32)`): The movie card's short, defined grounding shadow.

### Named Rules

**The Structural Shadow Rule.** A shadow may explain which surface is above another, but it may not be added simply to make a card look premium.

**The Reduced Transparency Rule.** When reduced transparency is requested, translucent layers become solid raised-night surfaces and backdrop blur disappears.

## 5. Components

Components should feel tactile and confident while behaving like familiar mobile controls.

### Buttons

- **Shape:** Gently rounded rectangles (`rounded.md`) for standard actions and full circles only for icon controls.
- **Primary:** Projection White with Dark Ink, 54 pixels high, and used for exactly one dominant action per state.
- **Hover / Focus:** A one-pixel lift is reserved for pointer devices, active state compresses slightly, and keyboard focus uses a two-pixel Signal Violet ring with a two-pixel offset.
- **Secondary / Ghost / Danger:** Secondary uses a restrained translucent or Raised Night surface, ghost is transparent, and danger uses Danger Rose only for destructive meaning.

### Chips

- **Style:** Full pills are allowed because chips represent compact filters, interpreted signals, or progress states.
- **State:** Selected chips use a meaningful signal color plus text or icon treatment so color never carries state alone.

### Cards / Containers

- **Corner Style:** Routine surfaces use 12 to 16 pixels, while movie art is clipped to 16 pixels.
- **Background:** Matte Night and Plum surfaces for utility work, with real portrait poster art on reaction cards.
- **Shadow Strategy:** Flat by default, with the Poster Anchor only on the primary movie surface.
- **Border:** Low-contrast full borders may separate utility surfaces, but colored side stripes are prohibited.
- **Internal Padding:** The four-pixel spacing grid controls every inset, with 16 pixels as the common phone gutter.

### Inputs / Fields

- **Style:** Familiar mobile fields use Raised Night or pale-sheet tonal contrast, a 12-pixel radius, and at least 48 pixels of height.
- **Focus:** A two-pixel Signal Violet ring with a two-pixel offset is mandatory.
- **Error / Disabled:** Errors explain the consequence and next recovery action, while disabled controls retain readable labels and expose their state semantically.

### Navigation

Navigation is deliberately small because WatchSignal is a focused flow rather than a multi-destination catalogue.
Back closes the deepest active surface before changing the underlying stage, Home starts a fresh session, and installed-app Back remains inside WatchSignal.
Icon actions are at least 44 by 44 pixels and always carry an accessible name.

### Cinema Stage

Reaction cards and results use a real poster or landscape backdrop, a deterministic dark scrim, one serif movie title, compact metadata, one short fit line, and one dominant action cluster.
Results may add a score dial and a five-poster strip, but long evidence and utilities belong in sheets rather than beneath the reveal.

### Transition Chamber

Launch, handoff, shortlist generation, privacy sealing, and result matching may use short signature motion with almost no controls.
Every transition reflects real state, lasts no longer than the associated product operation, and becomes immediate or a simple crossfade under reduced motion.

## 6. Do's and Don'ts

### Do:

- **Do** design and verify the full flow first at 390 by 844 pixels, then check every supported width from 320 to 430 pixels and 200 percent text zoom.
- **Do** use real TMDB poster or backdrop art in recognizable movie surfaces and use a finished WatchSignal asset when a tactile hero object is needed.
- **Do** keep one obvious action, short human explanations, and progressively disclosed utilities on every state.
- **Do** preserve the exact privacy, recommendation-source, truthful-error, reduced-motion, focus, contrast, and safe-area contracts in `PRODUCT.md`.
- **Do** use the shared tokens and primitives before introducing a new local style.

### Don't:

- **Don't** make WatchSignal feel like a generic streaming-service clone, a gamer skin, neon decoration pasted over ordinary app structure, or a flat conservative utility app.
- **Don't** ship a surface that looks cheap, sparse without meaning, overcrowded with explanatory copy, or recognizably AI-generated.
- **Don't** use generic recommendation language, internal model terminology, repetitive source labels, or decorative dashboards in the normal household flow.
- **Don't** use oversized close-up faces, fake poster art, or hero imagery that overwhelms the product's purpose.
- **Don't** hide a weak or failed recommendation path behind an apparently valid fallback.
- **Don't** use gradient text, decorative glassmorphism, side-stripe accents, identical card grids, or oversized rounded cards as a shortcut to visual interest.
- **Don't** synthesize physical lighting, glow, blur, masks, or tactile objects in CSS when the design calls for a reviewed finished visual asset.

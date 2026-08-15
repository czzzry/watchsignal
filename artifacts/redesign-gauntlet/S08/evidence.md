# S08 Viewer/profile selection builder evidence

## Claim

The household can choose Couple, Husband solo, or Wife solo and resolve distinct stored identities without ambiguity.

## Contract

The UI preserves `PeopleMode` values, founder/wife actor mapping, distinct-profile protection, and the existing create/save callbacks.
Unresolved new-profile text remains present after a failed create.

## Boundary

`ViewerProfileSetup` owns the full-screen People utility presentation and public recovery copy.
It does not own session navigation, vote state, recommendation logic, or persistence implementation.

## Behavior

The setup board has one People entry point.
The utility names all three modes, exposes stored identity selectors, rejects duplicate names, and has one Continue action.

## Evidence

- Round-two focused S08/S09 integration and state run: 18 of 18 passing.
- Full web state suite: 112 of 112 passing.
- Web TypeScript check: passing.
- Production build: passing.
- Real isolated Chrome at 390 by 844: People opens in one tap; close receives initial focus; reverse Tab wraps to Continue and forward Tab wraps to Close; Escape closes and returns to the exact People opener.
- The complete `main` and global credits footer receive `inert` and `aria-hidden=true`, then restore their exact prior state on close.
- Clean 320, 390, 430, 390 by 568, and 200-percent-equivalent captures are stored in this directory.
- Reduced motion, reduced transparency, and forced colors were actively emulated and all three media queries reported active.

## Decision

Builder handoff only.
Acceptance belongs to the independent critic.

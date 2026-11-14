# Phase 3 — Shape Matching implementation

## Implemented

- Authenticated /shape-matching preview route and operator-only link from balloon
  controls. Not added to public participant token routes; no access bypass.
- Colorful circle, square, triangle and star; outline-style targets use a uniform
  color to require shape matching, not simple color matching.
- Pointer drag/drop and tap source then tap target; native keyboard buttons.
- Four practice trials, configurable 5–50 local preview trials and progress.
- Three wrong choices or 30 active seconds advances as unsuccessful; no endless
  retry. Each retry requires source reselection; wrong choice resets its position.
- Pause/resume, background-tab pause, end confirmation and completion screen.
- Local-only attempt state includes shape, outcome, wrong drops, first-attempt
  correctness and approximate active milliseconds. Paused time is excluded.
- Source/target layouts support narrow screens and visible keyboard focus.

## Verification

29 JavaScript tests passed: 21 balloon regressions plus 8 Shape Matching engine
tests. Covers finite completion, wrong-choice limit/reselection, pause timing,
timeout, duplicate matching, early stop and invalid inputs. JS syntax and Python
route AST parsing passed. Tests do not validate real touch/drag UI behavior.

## Limits / outstanding

This is an explicitly labeled LOCAL PREVIEW, not recorded participant play.
No database/session write, report, export, pairing or network synchronization is
claimed. Those belong to Phase 4. Refresh/close discards local attempts; it does
not silently restart a recorded run. Do not use for actual data collection yet.
The trial timing is browser preview timing, not validated research timing.

Visual browser, drag/touch/keyboard, zoom and tablet acceptance remain pending.
The full Python suite remains unavailable until project test dependencies are
installed. No running server/cameras, ZIP, GitHub commit or push in this phase.

The GitHub recovery baseline still differs from this October 11 working source;
do not patch its old task files piecemeal or claim it is already synchronized.

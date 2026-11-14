# Pop the Balloon completion checklist

Reviewed: 2026-10-04 (Asia/Singapore)

Legend: **[x]** implemented and software-verified · **[~]** implemented but still needs physical-device acceptance · **[ ]** intentionally not done yet

## A. Main game replacement

- [x] Pop the Balloon is the only selectable participant game.
- [x] Target Tap, Go/No-Go, Focus Match, Visual Search, and Pattern Memory are absent from the new-session UI.
- [x] Historical completed-session records and exports remain readable; no historical research data is changed or deleted.
- [x] Every recorded run stores task key `pop_balloon` and version `2.0.0-balloon`.

## B. Final session workflow

- [x] Select participant → Start session → automatic two-second camera/framing check.
- [x] Pair/open participant screen → required balloon practice → operator begins recording.
- [x] Correct-pop goal drives progress and automatic task completion.
- [x] Operator finishes monitoring, then opens the generated result/report.

## C–F. Modes, goals, age defaults, and difficulty

- [x] Easy uses Pop Any Balloon; correct taps advance progress and missed balloons do not.
- [x] Moderate, Hard, and Adult Standard use Target Color with selectable target color, distractors, missed targets, and false-response recording.
- [x] Goal presets: 10, 15, 20, 30; custom range: 5–50; general default: 20.
- [x] Completion is based on required correct pops, not displayed attempts.
- [x] Age defaults: Child 6–9 = 15/Easy; Pre-teen 10–12 = 20/Moderate; Teen 13–17 = 30/Moderate; Adult 18+ = 30/Standard.
- [x] Operator can change the recommendation and the final configuration is saved.
- [x] Easy/Moderate/Hard sizes, speeds, display durations, waits, and distractor proportions are distinct and tested.

## G–I. Presentation, palette, and participant screen

- [x] Exactly one active balloon per trial; previous presentation finishes before the next.
- [x] Controlled random position/timing keeps balloons outside the fixed HUD and decorative ground.
- [x] Large touch target; onset time, tap time, and session-relative times are recorded.
- [x] Coral, sky blue, turquoise, sunny yellow, purple, orange, green, and pink palette.
- [x] Deep navy/dark teal text and warm cream/pale aqua panels; no pure black, pure white, or grayscale game design.
- [x] Text and swatch/icon identify the target, so instructions are not color-only.
- [x] Participant UI includes title, goal, progress, colorful bar, instruction, animated balloon, and calm background.
- [x] Mouse, touch events, Enter, and Space are supported; participant controls and technical/diagnostic information are hidden.
- [x] No visible countdown timer; fullscreen is requested after participant interaction.

## J–K. Operator screen and practice

- [x] Operator sees participant, pairing state, mode, difficulty, goal, target color, sound, and task state.
- [x] Start/repeat/cancel practice, begin recording, pause, resume, early end with reason, and monitoring stop are available.
- [x] Correct, incorrect, missed, and progress counters are displayed with friendly recovery messages.
- [x] Practice contains five samples, follows the selected mode/difficulty, and requires the correct pop/wait behavior.
- [x] Practice can be repeated and is excluded from recorded trials and calculations.
- [x] Recorded game cannot begin until practice is complete for the same participant/configuration.

## L–N. Animation, completion, and safety

- [x] Gentle floating/entry motion, short pop animation, particles/stars, optional soft sound, and reduced-motion behavior.
- [x] Tap time is captured before the animation; there are no flashing or strobe effects.
- [x] Goal completion stops new balloons and rejects duplicate completion taps.
- [x] Participant completion copy includes “Great job!”, “Task completed,” and “Please wait for the researcher.”
- [x] Operator receives completion state; completion time is saved; report is available after session stop.
- [x] Maximum attempts = 3× goal; configurable maximum duration defaults to five minutes.
- [x] Operator pause/resume and early termination reason are persisted.
- [x] Disconnect auto-pauses; reconnect auto-resumes; refresh replays only the unfinished planned balloon without duplicating the row.

## O–Q. Reproducibility, per-balloon data, and summaries

- [x] Cryptographic random seed is generated and stored before recording.
- [x] Complete recorded sequence is pre-generated and saved separately from practice.
- [x] Exact color, target/distractor flag, position, size, speed, display/wait timing, and maximum-three-consecutive-target rule are saved.
- [x] Per balloon: sequence, colors, target state, X/Y, size, speed, onset/tap timestamps, reaction time, response/scoring flags, phase, premature taps, tracking snapshot, and pause context.
- [x] Summary: goal, pops, false pops, missed targets, attempts, accuracy, completion time/status, mean/median/variability/fastest/slowest reaction time, premature taps, tracking validity, termination state, and quality warnings.

## R–S. Database, reports, and exports

- [x] Additive database migration supports new run/trial fields and fresh databases receive the schema automatically.
- [x] Run configuration JSON contains version, settings, seed, and full sequence.
- [x] Raw video remains disabled/not stored.
- [x] Report shows Pop the Balloon configuration, goal, mode/color, outcome counts, completion time, and response statistics.
- [x] CSV contains flattened balloon metadata; JSON preserves exact configuration/seed/sequence; database backup contains the new rows.
- [x] Historical exports remain compatible; every report states research use only and does not claim an ADHD diagnosis.

## T–V. Recovery, accessibility, and automated testing

- [x] Friendly handling for missing pairing, expired token, missing session/practice, duplicate start/tap, interruption, browser refresh, pause, early end, and session stop during an active game.
- [x] Large controls, responsive layout, visible focus, accessible labels, keyboard response, text-plus-color target indicators, reduced motion, and no intentional scroll lock.
- [x] Easy/Moderate/Hard, custom limits, completion, miss, false response, duplicate tap, practice exclusion/replay, pause/resume, abort, disconnect/reconnect, refresh recovery, persistence, exports, backup, historical compatibility, token security, and session/report paths are covered.
- [x] Full suite: **182 passed**; Python compilation, JavaScript syntax, and dependency checks passed.

## W. Actual browser/device acceptance

- [x] In-app browser mouse gameplay, secure pairing, required practice, five-pop complete game, automatic completion, session stop, report render, session ZIP, and database-backup ZIP.
- [~] Responsive CSS and touch event paths are implemented; confirm on the client's physical laptop touchscreen and tablet.
- [~] Pause/resume and disconnect/reconnect are automated; confirm with an actual Wi-Fi interruption.
- [~] Fullscreen and sound are implemented; confirm in the client's target browser/speaker setup.
- [~] Confirm 125–150% native browser zoom and all intended physical screen sizes.
- [~] Run one consented real-camera participant session; browser QA used clearly labeled simulated data.

## X. Documentation and release

- [x] README, first-time setup guide, operator manual, startup/connection guide, task field guide, modes/defaults, saved fields, and non-diagnostic limitation updated.
- [x] Current test count updated to 182 and obsolete selectable-game wording removed from active documentation/UI.
- [x] Privacy scan found no embedded access key/token in source or documentation and no generated ZIP in the project.
- [ ] Final clean client ZIP is intentionally not built yet, per owner instruction.
- [ ] Before the final ZIP: complete the physical items above, then exclude `.env*`, databases, logs, caches, access keys, test outputs, and participant data.

## Current release decision

The software implementation is complete and software-verified. Final deployment acceptance remains dependent on the five **[~]** physical-check groups in section W. No final client ZIP has been created.

# Pop the Balloon — operator and research field guide

Updated: 2026-10-04
Task key/version: `pop_balloon` / `2.0.0-balloon`

This is a research-support activity. It does not diagnose ADHD, calculate an ADHD probability, or provide treatment advice.

## Operator flow

1. Select a participant and start the monitoring session. The normal two-second camera/framing check runs automatically.
2. Open **Pop the Balloon** from the active-session workflow.
3. Confirm the age recommendation or deliberately adjust the difficulty, mode, goal, target color, sound, and safety duration.
4. Create the secure participant-screen link/QR and open it on the participant tablet.
5. Run the five-balloon practice. Repeat or cancel practice if instructions are not understood. Practice is never stored as recorded trials.
6. Select **Begin recorded game**. Pause/resume when needed. If the game must end early, select the reason before ending it.
7. The task completes automatically at the required correct-pop goal. Finish the monitoring session to finalize the report and exports.

## Modes, defaults, and limits

| Profile | Recommended goal | Level | Default mode |
|---|---:|---|---|
| Child 6–9 | 15 | Easy | Pop Any Balloon |
| Pre-teen 10–12 | 20 | Moderate | Target Color |
| Teen 13–17 | 30 | Moderate | Target Color |
| Adult 18+ | 30 | Standard | Target Color |

Goal presets are 10, 15, 20, and 30; custom goals are limited to 5–50. The general default is 20. The hidden maximum is three times the goal in attempts. The recommended duration guard is five minutes and is configurable from 1–10 minutes.

Easy uses large, slow, long-duration balloons and makes every balloon a target. Moderate uses medium balloons and normal timing. Hard uses smaller/faster balloons, shorter presentation, randomized waits, and a higher distractor proportion. Only one balloon is active at a time and its planned position is kept inside the play field, away from the instruction and progress panels.

## Saved research fields

Each run stores participant/session linkage, task key/version, age profile, level, game mode, target color, goal, maximum attempts/duration, sound setting, random seed, complete pre-generated sequence, status, termination reason, and start/completion timestamps.

Each recorded balloon stores trial number, balloon color/code, target color, target/distractor flag, intended X/Y position, size, speed, display/wait timing, UTC onset, session-relative onset, UTC response, session-relative response, reaction time, response/correctness/miss/false-response flags, premature taps, recorded phase, face/body tracking snapshot, and continuous/resumed context.

The summary reports required goal, correct pops, incorrect distractor pops, missed targets, attempts, accuracy, completion time/state, mean/median/standard-deviation/minimum/maximum valid reaction time, premature taps, valid-tracking attempts/duration, and data-quality warnings. JSON preserves the full configuration and sequence. CSV flattens per-balloon metadata. SQLite backup contains the corresponding database rows. Older task types remain readable in historical reports and exports.

## Recovery and accessibility

- A completed tap is accepted once. Duplicate completion requests are rejected.
- Pause or connection loss discards only an unfinished presentation, then replays the same planned balloon after recovery.
- Participant refresh recovers the unfinished trial without duplicating stored data.
- Mouse, touch, Space, and Enter are supported. Controls have visible focus, large targets, responsive layouts, text plus color instructions, and reduced-motion behavior.
- Participant screens never show researcher controls, camera/tracking errors, technical values, diagnostic results, or a visible countdown timer.

## Release boundary

The current full suite has **182 passing automated tests**. It verifies scoring, goals, practice exclusion/replay, randomization metadata, pause/recovery, early ending, active-game session stop, security, database migration, reports, exports, and historical compatibility. Browser-driven QA also completed pairing, required practice, a five-pop recorded game, automatic completion, session stop, and report rendering. Physical touchscreen, tablet, Wi-Fi interruption, speakers, fullscreen, and an actual participant run must still be smoke-tested on the approved deployment hardware before release.

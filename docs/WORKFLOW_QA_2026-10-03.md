# Operator workflow audit — 3 October 2026

## Scope and evidence boundary

Interactive browser walkthrough used an isolated mock server on port 8001, a separate temporary SQLite database, and participant `QA-WORKFLOW`. No actual participant/session records were created or overwritten on port 8000. A clearly labeled simulated room-profile fixture was used because mock mode deliberately does not support physical eye/head calibration.

This is software/UI evidence, not clinical validation or physical-device acceptance. No checks were fabricated as passed for an actual participant.

## Reproduced and corrected defects

1. Hidden calibration panels remained visible because grid/flex styles overrode the native `hidden` attribute. Shared styles now enforce hidden panels.
2. Participant-profile navigation still referenced a removed panel, producing a null-property error.
3. Late readiness responses could disable Stop session after active-session restoration. Responses now check request generation, selected participant, and active-session state before applying changes.
4. Reloaded dashboards did not reliably restore the active participant or explain the next task step. Active-session synchronization now restores context and exposes the task handoff.
5. Calibration navigation prompted about leaving even when progress was already autosaved. The warning now applies only to an in-progress calibration capture.
6. Hidden calibration steps eagerly opened camera streams. Previews now run only for the visible system-calibration step and are stopped during verification/navigation.
7. Task setup reported Ready when pairing/practice was still required, or when a task had finished. State labels now distinguish session needed, pairing, practice, recording and completion.
8. Participant connection header remained Checking server while polling was connected.
9. Missing stored head/body samples appeared as zero movement counts. Reports now show unavailable readings rather than implying measured zero.
10. Mock reports were not consistently labeled simulated; warning arrays rendered stray commas. Simulated data is labeled and warning paragraphs are joined correctly.
11. Collapsed calibration step labels lacked useful accessible names. Each step button now has its full name.
12. Shared dark glossary surfaces could fall back to a white background. The shared surface token is now respected.

## Walkthrough performed

- Created and saved the isolated participant through the Participants screen.
- Navigated readiness and placement steps; exercised all nine simulated placement controls.
- Verified physical eye calibration returns a clear mock-mode limitation; it was not recorded as a physical pass.
- Selected the participant and confirmed the four simulated pre-session checks.
- Started a session using the ordinary Start session control, without a verification override.
- Paired the participant-only display; it remained in the waiting screen until launch.
- Completed practice, then launched Go / No-Go, Adult / Easy, 15 recorded trials.
- Exercised pause and resume; participant display reached Task complete.
- Restored the active session on a fresh dashboard load and stopped it.
- Opened the completed report and checked participant/session identity and trial count.
- Export endpoint returned HTTP 200, an attachment filename, and an intact archive containing session JSON, manifest and seven CSV files. The in-app browser did not deliver a download event, so browser download completion remains unverified.
- Checked Participants, Settings, Hardware, Access management, Records and Live monitor: no observed console errors or horizontal overflow at the sampled viewport.
- Checked dashboard/report at 1520×900, 1024×768 and 390×844: no horizontal overflow or visible hidden panels.
- Verified camera-preview counts: readiness 0, placement 2, verification 0; returning to Dashboard succeeded.

## Still requires acceptance

- Actual eye baseline, neutral-head and directional checks with a cooperative person on camera.
- Actual body-joint visibility, controlled movement, posture and tracking-loss recovery.
- Physical tablet touch, real network disconnect/reconnect and full real-mode participant recording.
- Native screen-reader and true browser-zoom acceptance, beyond viewport checks.
- Browser download/print/PDF behavior in the client's browser.
- Full visual review of every error, empty, busy and permission state; sampled screens do not prove every state.

Temporary overrides remain explicit and recorded as unverified. They are not replacements for measured calibration and should not be treated as diagnostic validation.

## Release

## Automated regression evidence

Final full-suite result: **197 passed, 2 dependency-deprecation warnings**, completed in 67.75 seconds. This is software regression evidence, not physical calibration validation.

The completed simulated-session report screenshot was retained as local QA evidence and is not included in the clean client package.

The existing upload ZIP predates these fixes. No replacement ZIP was produced in this audit round.

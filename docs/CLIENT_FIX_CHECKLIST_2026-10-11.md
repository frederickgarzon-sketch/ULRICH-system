# Client feedback fixes — 2026-10-11

Source: `C:\Users\Freecom\Desktop\Behavior-Monitor-Research-Console-CLEAN`

No release ZIP was built or updated. Existing participant/session records and local login configuration were not wiped or changed. QA used separate mock databases (`data/fix-qa-20261011.db`, `data/followup-qa-20261011.db`) and port 8011, not the production database/cameras.

## Implemented and software verified

- [x] Circular neutral-head median handles angles straddling +180/-180 instead of producing a false zero baseline.
- [x] Shortest-arc pose smoothing; direction hysteresis and 250 ms hold reject one-frame direction changes.
- [x] Independent horizontal (left/right/center), vertical (up/down/center), and tilt labels in the face/head API and live monitor.
- [x] Missing/degenerate/inconsistent pose estimates show unknown angles, not stale directions. Offline snapshot clears angles and direction.
- [x] Moving-head baseline is rejected with a hold-still/retry message.
- [x] Practice gives explicit tap/wait instructions, at least 3 seconds per presentation, and at most 3 retries per item.
- [x] Practice-help notice survives heartbeat refresh and is visible to the operator; a new practice clears it. Practice is not silently marked passed.
- [x] Recorded tap and timeout progression tested for all eight colors, including sky blue.
- [x] Late tap becomes a nonresponse, not a reaction time outside the accepted display window.
- [x] Duplicate tap guard and cleanup; animation failure cannot strand the presentation promise.
- [x] Requests have a timeout; completion acknowledgement can be reconciled with the saved current-run trial.
- [x] Submission failure does not automatically replay the balloon. Explicit retry/help screen; participant error pause keeps completed attempts saved.
- [x] Accessible button activation and Space/Enter support; hover transform no longer conflicts with general button hover.
- [x] Report replaced with Behavioral Session Records: counts, target response timing, blink/body/head records, phases, coverage, trial table, notes, and export/print controls.
- [x] Visible report has no risk badge, composite score, or ADHD/No-ADHD verdict. API/export includes descriptive research features; optional offline research calculation remains separate.
- [x] Nonresponses show no reaction time. Chart excludes distractors/nonresponses instead of converting null to zero.
- [x] No valid movement/eye data is shown as unavailable, with coverage warnings, rather than an interpreted zero movement/rate.
- [x] Printable trial details open before printing and restore afterward.
- [x] Frontend cache version updated for the game.
- [x] Practice balloon is hidden before the timed presentation begins, including repeated practice. Browser testing exposed an initially visible, non-accepting balloon; this was fixed and practice completed 5/5 afterward. This does not prove the exact cause of the client's dark-blue issue.
- [x] Missing numeric measurements consistently use `Not available`; nonresponse trial reaction time remains `—`. Naive database UTC timestamps are localized correctly.
- [x] Report reflow verified at 390, 768 and 1280 px; CSS zoom reflow verified at 125% and 150%. These are not native browser-zoom acceptance tests.
- [x] A4 PDF pagination visually reviewed across five pages with a 45-row trial table: repeated table headers, wrapped cells, no clipped rows. Print details restore after printing.

## Test evidence

- Complete Python suite: **197 passed**, two dependency deprecation warnings; isolated test database, mock cameras. Includes wrapped baseline persistence, moving-baseline rejection, and stale-pose clearing.
- Node participant-controller regression suite: **19 passed**. Tests actual controller functions for tap/timeout of all eight colors, duplicate taps, late taps, animation exceptions, and initial practice visibility.
- Follow-up browser suite: **30 checks passed** (`tests/browser_followup.cjs`, `qa/followup/results.json`). All eight colors in Easy and Target Color modes; submission rejection and lost-ack recovery; actual isolated mock-server practice, pause/resume, unfinished-trial refresh, disconnect/reconnect; saved counts/timing and export consistency; missing values, escaped notes, responsive reflow and PDF generation. Browser pointer/touch emulation is not physical touchscreen acceptance.
- Latest full Python rerun after the practice fix: **197 passed**, two dependency deprecation warnings. No failing tests.
- JavaScript syntax checks: attention-task, dashboard, report.
- Browser smoke run: five correct pops reached the goal. Three successfully tapped balloons were **Sky blue**, two others Pink/Purple. Three earlier unattended presentations timed out and advanced. Saved report: five correct pops, three misses, eight completed attempts, goal reached. No console warning/error on the report.
- Browser report checked visually, including expanded trial table and missing-tracking warnings. Screenshot: `qa/behavioral-records-20261011.png` (simulated data).
- Browser practice run confirmed bounded retries; it also exposed a heartbeat-overwritten help message, subsequently fixed and API-tested.

## Not yet accepted — do not mark complete

- [ ] Actual deployed face camera: center stability, all five head directions, mirrored/non-mirrored mapping, and lighting/occlusion. Software tests do not establish physical-camera mapping or clinical accuracy.
- [ ] Exact client device's reported dark-blue loop reproduced/retested on its hardware. Sky-blue browser run passed here; the client's exact failure cause remains unproven.
- [ ] Physical touchscreen/tablet taps, practice completion and distraction behavior.
- [ ] Actual Raspberry Pi stream loss/reconnection with cameras and real sessions.
- [ ] Native 125–150% browser zoom and actual screen-reader review. Native computer-use testing stopped because the tool could not confidently verify the current browser URL; no native zoom acceptance is claimed. Headless browser viewport/CSS-zoom tests and PDF visual QA passed separately.
- [ ] Release ZIP/build — intentionally withheld until user approval.

## Next actual-device acceptance

1. Restart the updated CLEAN server so loaded Python code is refreshed. Do not start a second server on port 8000.
2. Keep the existing room/camera configuration. Recalibrate the head baseline once if its old saved baseline was erroneous; do not wipe data to do this.
3. Hold center, then turn left/right and up/down; observe the separate axes and return-to-center behavior.
4. Run practice then recorded balloon task on the client display, including sky-blue taps and intentionally missed balloons.
5. Finish the monitoring session; compare stored trial rows, coverage, report and downloaded exports.

Known limitation: the synthetic QA run has zero real tracking coverage. Its blink/movement readings are unavailable and cannot be used as participant measurements.

The responsive/PDF stress fixture expands the trial table to 45 rows for layout testing; its summary is not a participant calculation-validation dataset. Saved-record calculation checks use the separate completed five-pop mock session.

## Separate original-formula follow-up (not completed by these fixes)

- [ ] CLI/DataFrame output.
- [ ] P-001 regression fixture against the original provided formula.
- [ ] Exact original blink-duration rules and research validation.

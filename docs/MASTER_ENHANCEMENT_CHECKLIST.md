# Master enhancement checklist

Last software review: 2026-10-03 (Asia/Singapore)

Status legend: **Done** = implemented and software-tested; **Device test** = implementation exists but requires physical acceptance; **Pending** = not yet accepted.

## Guided workflow

- **Done** — One ordered operator flow: Cameras → Room setup → Participant → Quick check → Activity → Results.
- **Done** — Current step, progress, one Continue action, Back action, blockers, and Check again are shown together.
- **Done** — Selected participant persists locally and an active session restores after refresh.
- **Done** — Starting a session advances to Activity; stopping asks for confirmation and opens the report.
- **Done** — Calibration/readiness bypasses were removed from UI and API.

## First-login setup and daily operation

- **Done** — The first valid owner/admin login opens a database-backed six-step setup wizard.
- **Done** — Setup progress survives refresh, browser closure, and browser-history cleanup.
- **Done** — The wizard covers system/dependency checks, connection type, camera assignment and preview, room placement, calibration, participant-screen connectivity, and final review.
- **Done** — Camera-setting changes require a server restart and resume at the saved step; the wizard cannot silently finish against stale sources.
- **Done** — Completion records the time, operator, configuration fingerprint, calibration schema, and accepted room-calibration profile.
- **Done** — Critical configuration changes invalidate setup and route to the exact repair step.
- **Done** — Temporary camera faults preserve the saved setup and open the daily Dashboard with a focused repair warning, while Start Session remains disabled.
- **Done** — After completion, the Dashboard shows only Select participant → Start session, plus active-session and report actions; the live check is automatic.
- **Done** — Camera/network/calibration/diagnostic controls moved to protected **System Setup** and require a fresh owner/admin key confirmation for changes.
- **Done** — Run setup again and confirmed Reset saved setup actions are available to owners/admins.

## Camera setup and stability

- **Done** — USB, Raspberry Pi, and Custom source modes.
- **Done** — Safe USB detection that does not reopen a camera already owned by the server.
- **Done** — Friendly USB labels, separate face/body assignment, live previews, Swap, and Pi connection test.
- **Done** — Duplicate physical sources are rejected when saving.
- **Done** — Runtime duplicate-source guard opens only one native camera reader instead of risking a Windows crash.
- **Done** — Resolution/FPS/processing controls are under Advanced settings.
- **Done** — Startup message distinguishes normal stop from unexpected exit/start failure.
- **Device test** — Confirm a second USB camera at index 1 and Raspberry Pi streams on the client network.

## Room and participant readiness

- **Done** — Room setup is explicitly owner/operator work and has no participant selector.
- **Done** — Six guided steps, live framing guides, exact correction messages, retry controls, Back/Continue, saved progress, review and acceptance.
- **Done** — Actual required checks gate acceptance in real mode.
- **Done** — Participant can be selected or quickly created from Start monitoring.
- **Done** — Daily operation is reduced to Select participant → Start session; no second manual calibration is shown.
- **Done** — Start session performs a silent two-second live camera/framing check and gives one focused operator correction if it fails.
- **Device test** — Eye/head directions, body joints, lighting and distance with a consenting test participant.

## Activity and participant display

- **Done** — Recommended age/difficulty/trial defaults, compact task choices and pre-launch summary.
- **Done** — Pair display → Practice → Recorded task gate; no second active task is allowed.
- **Done** — Participant-only waiting, practice, task, paused, reconnecting and finished screens.
- **Done** — Finished message asks the participant to wait for the researcher.
- **Done** — Operator Pause/Resume endpoints and persistent session Stop control.
- **Device test** — Touch response, QR pairing, remote pause/resume and reconnect on the actual tablet.

## Errors, recovery and reports

- **Done** — Camera readers reconnect automatically and errors provide corrective actions.
- **Done** — Guided workflow and shared request errors include Retry and plain-language recovery steps.
- **Done** — Technical settings/details are collapsed away from normal use.
- **Done** — Reports distinguish completed/stopped/interrupted status, simulated data, unavailable readings and data-quality warnings.
- **Done** — Report actions: Start another session, Export full data, and Print/PDF.
- **Done** — Results remain explicitly non-diagnostic.
- **Device test** — Physical camera/network disconnect and reconnect; client-browser export and Print/PDF.

## UI, responsive and accessibility

- **Done** — Larger base text and controls, consistent guided cards, status text plus icons, visible keyboard focus and dark/light support.
- **Done** — 1024×768 and 390×844 checks found no horizontal overflow.
- **Done** — Mobile camera actions stack full width and the Save bar no longer covers content.
- **Done** — Hidden panels remain hidden and wizard steps have accessible names.
- **Device test** — Native screen reader, physical keyboard-only pass, tablet touch, and browser 125–150% zoom acceptance.

## Verification and release

- **Done** — 233 automated tests passed after the simplified two-step daily workflow, silent automatic start check, integrity/security audit, seated upper-body readiness, multi-frame joint-stability, calibration-feedback, and preview-stream reliability updates; Python and JavaScript syntax checks passed.
- **Done** — Isolated mock-browser walkthrough covered guided workflow and camera setup at desktop/tablet/mobile widths.
- **Done** — Isolated real-mode test with one USB source remained healthy; face connected and body reported a safe configuration conflict instead of crashing.
- **Pending** — Complete the physical acceptance items above.
- **Pending** — Build the final client ZIP only after physical acceptance. The ZIP must exclude `.env`, `.env.backup`, databases, logs, caches and test artifacts.

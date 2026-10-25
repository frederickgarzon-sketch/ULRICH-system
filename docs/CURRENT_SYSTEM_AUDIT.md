# Current system audit — 2 October 2026

> Historical audit. Current completion and acceptance status is maintained in
> `FINAL_COMPLETION_STATUS_2026-10-03.md`; older counts below remain as audit history.

## Integrity and release audit — 4 October 2026

- Full source inventory reviewed across backend/API, database, camera workers, AI processing, setup/calibration, session/task/report flow, frontend, startup, Raspberry Pi node, exports, backup/restore, documentation, dependencies, and clean packaging.
- Corrected the body-camera acceptance mismatch so hardware validation and calibration both use the documented 8 FPS minimum.
- Added strict update validation for participant dates and diagnosis-status values.
- Escaped backend/configuration text before rendering it in hardware, settings, calibration, and signed-user UI surfaces.
- Normal startup now disables raw HTTP access logging so short-lived participant pairing tokens are not retained in request logs; application/audit/error logging remains enabled.
- Fresh-install settings now match the seated upper-body profile, while knees/ankles remain optional rather than blocking.
- Added explicit runtime dependencies for Torch and psutil, documented the pose-model size and SHA-256, corrected the session-secret documentation, and removed personal paths/MAC addresses from shareable text.
- Temporary clean-package audit contained 161 entries and zero forbidden `.env`, database, log, cache, bytecode, virtual-environment, or imported private-reference entries. The audit ZIP was deleted afterward; no final ZIP was built.
- Isolated runtime smoke test loaded all main pages and completed participant creation → session → secure pairing → practice → five recorded trials → stop → report → research ZIP export.
- Full automated result: **227 passed**, with two upstream Starlette/httpx/anyio deprecation warnings and no application-test failures.

Physical Raspberry Pi, real-camera, participant, tablet/touch, and network-reconnect acceptance still requires the actual client hardware and must not be represented as software-passed.

## Interactive workflow audit — 3 October 2026

See [the operator walkthrough and remaining acceptance work](WORKFLOW_QA_2026-10-03.md). This later pass reproduced actual UI defects involving hidden panels, removed controls, asynchronous session state, preview streams and report availability. A separate mock database was used for a participant → readiness → session → pairing → practice → recorded task → stop → report walkthrough. Physical calibration was not fabricated as passed. Earlier completeness claims and test counts should be read as historical snapshots.

## Completion pass — 3 October 2026

### Newly completed

- Main server started successfully on port 8000 in real mode. Health returned `status=ok`, `mode=real`. The authenticated active-session check returned IDLE.
- Fixed a reviewer privacy leak: participant/session list endpoints now enforce the same account scope as individual record/report endpoints.
- Added authenticated role-matrix tests for owner/admin/operator/reviewer lists, records, reports, JSON/ZIP session exports, account administration, reviewer write protection and unauthenticated access.
- Added checked JSON requests and recovery text for HTTP 401/403/404/409/413/422/429/500/503, network failure and non-JSON responses. Failed writes are not automatically repeated.
- Fixed accessible names for participant search, history filtering and paired landmark display/measurement checkboxes.
- Expanded readability fixes to labels/supporting text/navigation and login. Added a collapsed measurement glossary to operator screens; participant screens do not receive it.
- Fixed dark settings buttons that used white text on a light-cyan background; they now use dark text.

### Fresh verification

- Full isolated suite: **190 passed**, two dependency deprecation warnings, 47.05 seconds. Later targeted helper/privacy checks: six passed.
- Browser review: **36 combinations** across 12 main pages at 1520px, 1024px and 390px widths. No document-level horizontal overflow or unnamed visible inputs in those checks. Report page used a separately created QA-only record.
- Settings keyboard Tab moved from face source to body source. Inspected settings labels/supporting text are at least 14px. Dark button foreground/background were measured from rendered styles after correction.
- These checks do not establish complete screen-reader compatibility, full visual acceptance of every wizard state or true browser-zoom acceptance.

### Remaining concrete blockers

- Pi hostname resolution failed and the last known Pi address `192.168.0.227:8090/health` timed out. Physical face/body calibration, tablet touch, client-router reconnect and complete real-device session acceptance remain blocked until the devices are reachable.
- Actual screen-reader and 125–150% browser-zoom acceptance remain unperformed. Responsive viewport checks are separate evidence.
- Main server started before the newest reviewer-list backend fix. An authenticated idle check was completed, but the controlled restart command was blocked by execution policy. Do not claim the newest backend fix is loaded until the server is restarted and smoke-tested.
- Build/ZIP confirmation was requested; no approval has been received. Client ZIP remains unchanged.

Earlier audit sections below are retained as history. This completion pass takes precedence for current startup/test evidence.

## Follow-up audit — 3 October 2026

Source-only update; client ZIP is unchanged and still requires explicit build confirmation.

### Implemented and checked

- Shared readable, keyboard-accessible technical help for camera timing/resolution, blink/head/body thresholds and derived features.
- Plain-language API error formatting on task, calibration, settings, participant, account and session actions; validation arrays no longer become `[object Object]`. Unexpected rejected requests show a recoverable alert without retrying writes automatically. This does not mean every possible application failure has been individually injected.
- Larger operator base text, labels, input fields and buttons. Settings help stays within each field's grid cell instead of displacing neighbouring inputs.
- Recording confirmation now follows a fresh participant/session check, with duplicate-click protection. Changing participants clears stale age/level confirmations.
- Practice cancellation is generation-bound, preventing an old display from cancelling replacement practice.
- Pattern-memory practice now presents the reference before its response probe.
- Task operator page now creates a paired participant link and QR, with an explicit separation between researcher and participant screens.
- Participant directory and history text are escaped before insertion into HTML.

### Fresh evidence

- **185 tests passed**, two dependency deprecation warnings, 47.75 seconds.
- **80 API end-to-end combinations**: five activities × four age profiles × four levels. Every configured trial is completed; report participant identity, activity/age/level, correct counts, accuracy and JSON-export identity are checked.
- Shared JavaScript formatter/HTML escaping behavior tested under Node; JavaScript syntax checks passed.
- Browser QA: settings labels measured 14px with no horizontal overflow at the current 1280px viewport; aligned help/input layout inspected; no settings console errors. Participant directory renders; operator page shows the active test participant, adult recommendation, disabled recording before practice, and the paired link/QR.
- Browser and API fixtures use a separate mock database on port 8001; no live participant records or physical camera settings were changed.

### Current blockers / remaining acceptance

- Main server health at `127.0.0.1:8000` refused connection during this audit; no deployment/restart was performed.
- Both `adhd-camera.local:8090/health` and the last known Pi address `192.168.0.227:8090/health` timed out. This does not establish whether the Pi is powered off, has a different address, or is on another network.
- Physical camera calibration/movement validation, real tablet input and router disconnect/reconnect acceptance remain open.
- Full screen-reader and real browser-zoom acceptance remain open; a browser viewport check is not a substitute.
- Broader cross-screen visual/error acceptance remains open. Do not treat the 185 tests as 185 completed checklist items.

The sections below retain the previous audit history. The follow-up evidence above takes precedence for current test counts and availability.

## Release status

Source changes only. No new build or ZIP was made. The client-ready ZIP SHA-256 remains `31EA755CD6A758636EED367F5D4F09E0029D2D1DC369B2581BE105CBF7898D9A`.

The live server has not been restarted to load the backend changes. Tests use an isolated database/mock cameras; these tests are not evidence of physical camera accuracy. Real participant records and the Raspberry Pi were not modified by this audit.

## Completed fixes

- Room setup uses an operator-led local response-device check, independent of participant practice/session creation.
- Cancelled practice cannot be marked complete; stale practice generations cannot complete replacement practice.
- Active task routes enforce participant ownership for operators.
- Participant display pairing is session-bound; changing participants requires a new pairing. Opening a QR preview does not falsely mark the participant display connected.
- Camera snapshots reject missing or stale frames instead of reporting cached tracking as live.
- Recording/readiness checks reject changed room configuration, outdated room-profile verification, and missing required body joints.
- Recalibrating resets the associated baseline flag rather than leaving an old success state visible.
- Stopping a completed task preserves its completed database status.
- Response collection excludes fixation/reference phases and keeps the full response window; pause during fixation is respected before the next trial starts.
- Participant display heartbeat continues during activity; researcher cancellation stops the display. Reloading a completed activity shows completion.
- Calibration progress restoration checks configuration/operator context; guided body advancement rejects duplicate queued transitions.
- Partial calibration work can be saved as a draft; production acceptance still requires all required checks.
- Empty readiness data cannot unlock navigation. Polling cannot re-enable guided face controls while a sequence is busy.

## Verification

- Full Python suite: **103 passed**, with two dependency deprecation warnings (22.05 seconds).
- Seventeen isolated workflow regression cases cover practice cancellation/generation, session pairing, stale cameras, operator access, completed-status preservation, QR heartbeat and partial drafts.
- JavaScript syntax checks passed for every `static/js/*.js` file.
- Browser check on the isolated QA application: room setup displays “no participant required”; incomplete physical placement disables Continue; later steps remain locked.
- Earlier responsive/focus/footer checks are recorded separately in the 180-item checklist and have not been relabelled as fresh physical acceptance.

## Still open — do not mark the whole checklist complete

- Actual face direction, eye baseline, body movement and required-joint acceptance with the installed cameras and an operator physically present.
- Measured camera/network throughput and reconnect behavior using the client's router, tablet and Raspberry Pi.
- Complete participant end-to-end practice/recording/report flow on the final real setup, including all five activities and age/level combinations.
- Keyboard/screen-reader, actual browser zoom and tablet touch acceptance beyond the current automated/syntax checks.
- Source update deployment/restart, followed by a real-mode smoke test. Build/ZIP remains explicitly blocked until the user confirms it.

All “Acceptance pending” rows in UI_UX_ACCEPTANCE_CHECKLIST.md remain open. An implementation mapping is not a passed acceptance test.

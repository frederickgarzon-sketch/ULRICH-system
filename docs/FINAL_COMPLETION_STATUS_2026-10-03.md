# Final software completion and physical acceptance status

Review date: 2026-10-03 (Asia/Singapore)

This record separates implemented/software-tested behavior from claims that require the actual client hardware and a consenting test participant. A physical item is never marked passed from mock data.

## Implemented and software-tested

- [x] Unified owner-facing setup and system-calibration workflow; legacy system calibration redirects to the six-step setup.
- [x] Guided UP, DOWN, LEFT, RIGHT, CENTER coach in setup Step 5 with expected/detected feedback, retry, and two consecutive confirmations.
- [x] Direction results persist in the database, are invalidated by recalibration, and gate Continue/setup completion.
- [x] Live face/body previews, grouped-but-exact missing-joint guidance, focused placement repair, a seated upper-body POV/safe-zone guide, and collapsed passed checks. The default seated profile requires head/shoulders/arms/hands/hips; knees and ankles are recommended rather than blocking.
- [x] Calibration actions visibly show locked, ready, running/countdown, failed, completed, and database-saved states; accidental recalibration requires confirmation.
- [x] Only previews on the active setup step are connected, preventing hidden MJPEG streams from exhausting browser connections and stalling page scripts.
- [x] Step completion is derived from saved evidence instead of the highest visited page.
- [x] Setup invalidation covers cameras, tracking, measured FPS, eye/head calibration, and configuration fingerprint changes.
- [x] Final connectivity checks require a participant-screen heartbeat; Raspberry Pi mode also requires a live node-health response.
- [x] System checks perform a real database query, writable-file test, free-space check, dependency version inspection, and readable model-file check.
- [x] Neutral-head UI reports relative zero rather than confusing raw wrapped Euler angles.
- [x] Blink logic rejects excessive closures and persists minimum EAR plus closure duration.
- [x] Periodic face/eyes/head/body validity rows distinguish measured zero events from missing tracking.
- [x] Attention tasks use an exact target count, no four consecutive targets, a persisted random seed, and the persisted target sequence.
- [x] Baseline, task, and post-task phases are explicitly stored and used by research feature extraction.
- [x] Export schema 2.0 includes response fields, phases, validity, closure duration, and research features.
- [x] Reference-cohort import validates CSV structure and stores version, cohort, source, approval reference, SHA-256, importer, and timestamp.
- [x] Experimental score stays unavailable without an integrity-verified, approved, age-matched cohort of at least 30 rows; it remains explicitly non-diagnostic.
- [x] Backup verification and safe restore tooling are present; restore creates a safety copy before replacement.
- [x] Setup UI has visible focus, responsive desktop/tablet/mobile layout, dark theme, no horizontal overflow, and no scroll lock in automated browser inspection.
- [x] Clean-package builder is non-destructive and excludes `.env`, database/WAL files, logs, caches, Git metadata, bytecode, virtual environments, and imported private reference datasets.
- [x] Deployment security decision documented: isolated trusted LAN only for HTTP; HTTPS required before untrusted-network use.
- [x] Supported Windows/Python, USB and Raspberry Pi assignments, model file, package versions, target FPS, and placement requirements are documented in `SUPPORTED_HARDWARE_AND_VERSIONS.md`.

## Automated verification

- [x] 182 Python tests passed on 2026-10-04 after the Pop the Balloon replacement; JavaScript syntax check passed.
- [x] Python compile check passed.
- [x] Setup JavaScript syntax check passed.
- [x] Database additive migration passed on the current database.
- [x] Browser layout inspection passed at 1024×768 and 390×844 without horizontal overflow or hidden actions.
- [x] Backup export/verify/restore drill passed against a temporary target.

Two third-party deprecation warnings remain in the test runner (`starlette.testclient`/`httpx` compatibility). They do not indicate an application test failure, but dependency upgrades should be handled in a separate controlled release.

## Ready for physical acceptance — not yet honestly passable in software alone

- [ ] Confirm distinct face and body Raspberry Pi streams on the final client hardware.
- [ ] Confirm real face framing, lighting, 35–45 cm distance, blink detection, and all five head directions.
- [ ] Confirm real body framing, required joints, posture, and controlled movement with a consenting test participant.
- [ ] Confirm Raspberry Pi hostname/IP change, stream health, timeout, disconnect, and reconnect on the client D-Link network.
- [ ] Confirm QR/link pairing, touch response, pause/resume, reconnect, and completion on the final tablet/browser.
- [ ] Complete one full real flow: login → setup → participant → quick check → session → task → stop → report.
- [ ] Confirm downloaded ZIP/JSON/CSV, Print/PDF, and database backup on the client browser.
- [ ] Run native screen reader and physical keyboard-only acceptance.
- [ ] Verify actual browser 125% and 150% zoom on the client display.
- [ ] Run the final smoke test after copying to a fresh client computer.

## Release gate

Do not label the system “clinically validated,” “diagnostic,” or “physically accepted” until the applicable research validation and all physical acceptance items above are documented. Do not build or distribute the final client ZIP until the owner reviews this result and explicitly confirms the release build.

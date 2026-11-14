# Simplified workflow release — 2026-10-04

## Final operator flow

Fresh installation:

`Access-key login → six-step Initial System Setup → Save and finish → Operation Dashboard`

Normal daily use:

`Login → Select or add participant → Start session → participant activity → finish session → report`

There is no second visible participant calibration or Quick readiness step. Selecting **Start session** performs a silent two-second check of face camera, body camera, face/body tracking, required framing, measured FPS, and raw-recording privacy state. The session is created only after this check passes.

If the automatic check fails, the operator receives one focused correction and can retry **Start session**. The participant screen shows only a calm instruction to sit comfortably, look toward the cameras, and wait for the activity. Technical details remain on the operator side.

## Calibration responsibility

The six-step calibration belongs to the equipment and room. It is completed once during initial setup and repeated only after a relevant camera, mount, room, lighting, model, or tracking-configuration change. Eye baseline, neutral head, and the guided five-direction test remain part of that owner/operator setup; they are not repeated for every participant.

## Saved and audited state

- Setup completion and progress are stored in the database, not browser-only storage.
- Accepted calibration and its configuration fingerprint are retained.
- Each automatic session-start check saves its sampled result for the audit trail.
- A failed check does not create a monitoring session or participant measurement record.
- Raw video recording remains disabled.

## Verification completed

- Updated Dashboard inspected in the browser: two visible steps and `System ready` state.
- JavaScript syntax check passed.
- Current full automated suite passed: **182 tests**, including the Pop the Balloon replacement, early-end/session-stop behavior, practice replay, and historical-record compatibility coverage.
- The final client ZIP privacy scan excludes `.env`, `.env.backup`, databases, logs, caches, access keys, test outputs, and participant data.
- The client ZIP contains `.env.example`, application source, model file, startup scripts, tests, and current documentation.

## Release artifact

Use the newest ZIP whose filename begins with `Behavior-Monitor-Research-Console-FINAL-`. Extract it before running `run_windows.bat`. Each new computer generates its own private `.env`, access key, session secret, and blank database on first launch.

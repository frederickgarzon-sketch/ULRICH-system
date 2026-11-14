# Production hardening status

Updated: 2026-10-04

## Implemented in software

- Real-camera mode, separate face/body processing, measured health telemetry, and raw-video storage locked off.
- Owner/Admin one-time site calibration plus a silent two-second camera/framing check when each session starts.
- Named accounts, ownership isolation, six-digit PIN throttling, signed sessions, audit events, and protected administrator endpoints.
- Short-lived participant-display pairing. The tablet capability is limited to practice/status/trial calls and expires after 30 minutes.
- Separate protected researcher route (`/attention-task/operator`) and participant-only QR route.
- Remotely launched, unrecorded practice followed by researcher-controlled recording.
- Versioned Pop the Balloon runs with goal-based completion, reproducible stimulus plans, unrecorded practice, operator pause/resume, refresh recovery, detailed balloon metadata, and readable historical task rows.
- Explicit non-diagnostic reporting, machine-readable exports, integrity hashes, SQLite online backup, and interrupted-session recovery.
- Automated API, scoring, camera, pose, movement, performance-health, Raspberry Pi node, and protocol tests.

## Required before a supervised research pilot

- Run the documented hardware acceptance sequence on every approved laptop, Pi, camera pair, browser, and tablet model.
- Freeze exact hardware serial-to-role mapping, software dependencies, model file hashes, screen refresh rate, and task preset versions.
- Perform annotated blink, head-direction, posture, movement, dropped-frame, reconnect, and reaction-timing validation.
- Confirm consent/assent, ethics approval, retention schedule, deletion authority, incident response, and encrypted backup storage.
- Use Windows device encryption and a protected research account. Do not store exports in an unencrypted shared folder.
- Complete a backup restore drill and record its date and result.

## Required before clinical or diagnostic claims

- A prespecified study protocol, appropriate comparison standard, sample-size justification, and independent ethics/statistical review.
- Sensitivity, specificity, confidence intervals, calibration, subgroup performance, test-retest reliability, and external validation.
- Independent validation of every feature and any combined model on data not used for threshold/model development.
- Human-factors testing showing that operators, children, and guardians understand the workflow and limitations.
- Regulatory, privacy, and institutional approval applicable to the deployment location.

Until these evidence gates pass, outputs remain descriptive behavioral measurements and must not state ADHD/No-ADHD, probability of ADHD, subtype, severity, or treatment advice.

## Operational release checklist

1. All automated tests pass.
2. Real mode and authentication are enabled; raw-video storage is off.
3. Site calibration is accepted and the session readiness check passes.
4. Participant tablet is paired with a fresh QR capability.
5. Practice completes on the participant display.
6. Both camera health indicators remain acceptable throughout recording.
7. The report is reviewed for missing/invalid data before export.
8. Backup is created, encrypted at rest, and periodically restore-tested.

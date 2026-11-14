# Phase 4 — Shape Matching session/records integration

## Implemented

- Operator navigation links Balloon controls to Shape Matching. Practice/local
  preview remain clearly unrecorded. Operator creates a recorded run for the
  active monitoring session and receives a separate participant link.
- New additive SQLAlchemy table shape_matching_runs: linked session, token hash,
  saved randomized shape plan, versioned report payload and per-attempt rows.
  Normal database initialization creates this table; no real database was opened
  during this work. No claim of deployment migration acceptance yet.
- Eight-hour token, session-end rejection, operator access checks on run creation
  and stop. Participant endpoints only access their token-linked run. Tokens are
  never returned in report/export. Pairing URLs are private bearer credentials.
- Save each recorded attempt before allowing another. Duplicate retry with the
  same row is idempotent; conflicting/out-of-order rows, wrong planned shape and
  inconsistent outcome fields are rejected. Counts are derived from saved rows.
- Waiting/recording/paused runs block balloon launch/practice; active balloons
  block shape creation. These are single-server application guards, not a claim
  of cross-process atomic task scheduling.
- Pause/resume, early stop, failed-save recovery, saved-plan restoration, and an
  operator stop action for abandoned pairings. Completed attempts survive reload;
  an unsaved attempt restarts and earlier unsaved timing cannot be reconstructed.
  Pending-save data is in page memory only: do not refresh while save is pending.
- Shape Matching has its own report section and expandable rows. JSON has a
  shape_matching collection; CSV package adds shape_matching_trials.csv. Export
  schema is 2.1. Balloon counts are not combined with shape metrics.
- Session deletion removes its shape records. Report marks unfinished shape runs
  as interrupted when the monitoring session has ended.

## Data interpretation

Shape order is stored. Target layout is randomized client-side and not stored;
exact spatial layout reproduction is not supported yet. Trial data includes
shape, matched/timeout/assistance_limit/stopped outcome, client active_ms, wrong
choices and first-attempt flag. Summary first-attempt accuracy uses saved attempts
as its denominator, including unsuccessful/stopped attempts. Unattempted planned
items remain unfinished, not fabricated successes or failures. No ADHD verdict.
Client timing is descriptive/unvalidated, not a server-measured reaction time.

## Testing

Current result: **10 isolated Python tests passed; 29 JavaScript tests passed**.

- Isolated .venv-shape-tests installed minimal SQLAlchemy/dotenv/pytest tooling;
  ignored by Git. Full AI/runtime dependencies are NOT installed in this venv.
- Temporary SQLite tests cover durable plans/rows, idempotent writes, token and
  session boundaries, ordered trial validation, pause/stop, outcome consistency,
  separate report/JSON/CSV data and session-delete cleanup, abandoned-pair stop,
  and token expiry. No participant data is used. Export-package test is generated
  in memory from synthetic records, not a release ZIP on disk.
- Python/JS syntax checks and existing balloon/shape JS regressions run separately.

## Acceptance still pending — not production complete

- Full application HTTP authorization tests and full Python suite with all
  dependencies; visual browser/tablet and actual paired-device end-to-end tests.
- Operator live dashboard launch/pause/resume widgets and QR presentation are not
  unified; currently use separate Shape Matching controls and copy/open its link.
- Real-time cross-device stop notice, restart durability and unsaved-trial
  recovery UX require walkthrough. Operator stop invalidates subsequent writes
  but does not immediately push a stop message to an idle participant page.
- Print layout, downloaded export and fresh-install additive migration checks.
- Actual black-balloon complaint remains unverified on the client device.

No system server/cameras started. No release ZIP, commit or GitHub push. Source
remains in Documents/ChatGPT/ULRICH system-2026-10-11; GitHub still has the older
recovery baseline until an explicitly authorized source synchronization.

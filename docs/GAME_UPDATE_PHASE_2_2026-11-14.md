# Phase 2 — balloon loop repair, partial verification

Working source: Documents/ChatGPT/ULRICH system-2026-10-11.

## Reproduced before repair

Two new deterministic controller tests failed against the original source:
practice completion retained phase `practice` instead of `ready`, and concurrent
heartbeat calls issued two overlapping requests. A stale practice response could
therefore leave/re-enter a completed generation. This is a confirmed state
management defect, not proof of the client's dark-balloon root cause.

## Changes

- Assign the practice completion/help response phase immediately.
- Remember finished/help-stopped practice generation IDs locally so stale status
  responses cannot restart that same generation. New launches have new IDs.
- Serialize participant heartbeat requests, clearing busy state in finally.
- Bump the template's JS asset version to avoid using the cached old controller.
- Preserve finite three-try practice assistance and existing recorded behavior.

## Verification

- 21 JavaScript tests passed (19 existing plus two new regression tests).
- JS syntax check passed.
- New tests demonstrate failure before the repair and success afterward.
- Python test attempt could not run: available workspace virtual environment
  reports `No module named pytest`. No passing Python count is claimed.
- Tests use synthetic DOM/API responses, no live server, cameras or real data.

## Outstanding — do not mark the entire Phase 2 complete

- Exact dark/black appearance and actual-client loop reproduction.
- Full timed practice/recorded controller tests, pause/resume, refresh and
  reconnect matrix and visual browser/tablet checks.
- Python focused/full suites in an environment with project dependencies.
- No evidence yet for changing recorded trial scoring or color semantics.

Only local source/test/document changes. No server startup, ZIP, commit or push.
The GitHub recovery repository remains older and has not been synchronized.

# Phase 1 — actual balloon source inspection

## Working source and relocation

Working folder: Documents/ChatGPT/ULRICH system-2026-10-11.
All 168 files from the matching Desktop folder were compared by SHA-256 with
zero missing/different files before the Desktop duplicate was sent to Recycle
Bin at the user's request. The Documents copy remains intact.

This source contains Pop the Balloon, unlike the October 4 GitHub recovery
baseline. It has no own .git directory. Do not treat the old GitHub branch as
this source or copy only the JS over the older incompatible backend.

## Verified findings

- Frontend, backend, balloon-specific Python tests and JS regressions exist.
- Eight declared colors: coral, sky, turquoise, yellow, purple, orange, green,
  pink. No explicit black balloon ID; the user's observed black/dark appearance
  must be correlated with actual stimulus metadata/rendering, not assumed.
- waitForBalloon has a completion guard, timeout, phase watcher and animation
  exception recovery. Existing per-balloon tests pass: 19/19. JS syntax passes.
- These synthetic tests cover an individual balloon wait, NOT the complete
  practice/recorded loops, real CSS rendering or network/heartbeat interleaving.
- Practice intentionally repeats an incorrect example, up to three tries before
  requesting help. This may resemble looping, but is not proof of the complaint.
- On practice completion the frontend awaits practice-complete but does not
  immediately assign the returned ready phase to participantPhase. Heartbeat
  starts practice whenever the phase is practice and runningLoop is false.
  This is a potential stale-phase/re-entry window requiring a deterministic
  full-controller race test. It is NOT yet a reproduced root cause.
- Recorded play advances against server status and trial completion. Backend
  caps attempts at goal * 3 and has a configured wall-time safety limit.
  Repeated colors alone do not prove a repeated trial; compare IDs/numbers.

## Verification completed

- [x] Verify moved source and remove only the matching Desktop duplicate.
- [x] Locate actual balloon controller/backend/template/style/tests.
- [x] Inspect color IDs, retry bounds and completion/recovery logic.
- [x] Run existing JS regressions: 19 passed.
- [x] Record source evidence and distinguish hypotheses from confirmed bugs.
- [ ] Reproduce the reported dark-balloon loop in practice and recorded mode.
- [ ] Add a failing full-controller regression for the exact cause.
- [ ] Visual browser/tablet rendering and actual-client acceptance.

## Phase 2 targets

Test practice completion against stale heartbeat responses; finite wrong/missed
practice retries; recorded tap/timeout submission and duplicate input; network
retry and refresh recovery; actual computed balloon colors/hover/pseudo-elements;
and safety termination. Make changes only after confirming the relevant path.

No game code changed, no server/cameras started, no ZIP, commit or push.
No claim that the client issue is fixed. Python/full suite not rerun in Phase 1.

## Source fingerprints (before diagnosis document)

- static/js/attention-task.js:
  ED0A87D688C28963DB5BB0593E785311D52044D11A9EE871E3C555984984B5AF
- app/tasks/attention_task.py:
  322218699A2B94DAD47168D5B27798730ADD99AD6CBBF91D14208B7B61375AAB

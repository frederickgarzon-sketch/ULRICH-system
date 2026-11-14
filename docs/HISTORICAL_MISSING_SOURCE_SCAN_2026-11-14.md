# Two-game update — Phase 1 source diagnosis

Date: 2026-11-14

## Scope

Diagnose the reported black/dark balloon loop in practice and recorded play.
Do not modify game behavior in Phase 1. Planned second game: Shape Matching.

## Verified local baseline

- Repository: frederickgarzon-sketch/ULRICH-system, branch main.
- Inspected HEAD: 679d2dfa4c0c6d2d6701456266f412bf833a7aaf.
- Working tree was clean before this audit document was created.
- This is the October 4 recovery source, as documented in REPOSITORY_BASELINE.md.
- No fetch/pull, server startup, camera access, private data access, ZIP, commit
  or push was performed for this diagnosis.

## Evidence

- static/js/attention-task.js initializes selectedTask as target_tap.
- renderStimulus uses star/circle, GO/STOP, matching-symbol, visual-search and
  pattern-memory stimuli. It contains no balloon color IDs or balloon renderer.
- Practice uses four fixed boolean examples and a 1100 ms response window.
- Recorded play requests a trial, displays a timed stimulus, then submits its
  response and advances the local loop. This is not evidence about the client's
  balloon implementation.
- templates/attention-task.html and static/css/attention-task.css contain the
  corresponding older stimulus UI, not Pop the Balloon.
- The existing attention tests exercise those older tasks. Their passing would
  not verify the reported balloon problem.
- A filename search of the current ADHD workspace found no balloon regression
  test files or October 17 audit document. This was not an exhaustive scan of
  every disk, archive or remote branch.

## Diagnosis / limits

Confirmed issue: the available source baseline does not match the client's
reported balloon build. The exact runtime cause of the balloon loop is UNKNOWN.
It is not justified to blame a black/dark-blue color value, retry policy,
animation promise or request handling until that implementation is inspected.

No balloon-loop reproduction was possible from this baseline. No fix is claimed.
Do not replace a collaborator's newer game with these older task files.

## Phase 1 checklist

- [x] Inspect current local version, branch, remote and working-tree state.
- [x] Inspect participant template, JS controller, CSS and backend task source.
- [x] Check available game test coverage and baseline provenance.
- [x] Record evidence and the source mismatch.
- [ ] Obtain the actual balloon build/source or locate it on the remote/new PC.
- [ ] Reproduce black/dark balloon behavior in practice and recorded play.
- [ ] Identify exact cause and add a failing regression test before Phase 2 fix.

## Required next evidence

### Extended recovery checks

- Remote heads checked: only main at 679d2dfa4c0c6d2d6701456266f412bf833a7aaf.
- Current workspace source search: no balloon implementation found.
- Desktop TESTER source search: unrelated utilities, no balloon implementation.
- Matching Downloads archive search: no candidate game archive found.
- Read ZIP entries without extracting or changing archives: CLIENT-READY ZIP,
  LATEST-2026-10-03 ZIP and Phase 2 ZIP. Each contains older attention JS/backend
  files; none of those files contains a balloon implementation.
- These checks do not prove no copy exists anywhere. The client machine or an
  unprovided external backup may still hold the required version.

Phase 2 remains blocked by missing source. Rebuilding a new balloon game would
be a replacement implementation, not a verified fix of the client's build.

Obtain the folder or branch used on the client machine, especially
static/js/attention-task.js, static/css/attention-task.css,
templates/attention-task.html and app/tasks/attention_task.py, plus any separate
balloon modules. Exclude .env, credentials and participant databases.
Record its commit/version and reproduce both tap and timeout using synthetic
sessions. Establish which actual color/trial ID fails instead of assuming black
and dark blue refer to the same code path.

## Acceptance checks for subsequent phases

All colors advance exactly once on tap or timeout; duplicate input cannot repeat
a trial; finite practice and configured recorded completion; explicit request
failure recovery; pause/resume, refresh and reconnect do not silently replay
completed trials. Shape Matching must have separate game metadata/results.

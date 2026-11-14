# Repository baseline and collaboration

## Current source — 2026-11-14

The user located the October 11 source and moved it to
Documents/ChatGPT/ULRICH system-2026-10-11. All 168 original files were compared
with the Desktop duplicate before that duplicate was sent to Recycle Bin.
This Git checkout is now synchronized from that newer source, including local
Phase 2–5 Shape Matching/balloon practice and visual updates. The prior missing
source scan is retained as HISTORICAL_MISSING_SOURCE_SCAN_2026-11-14.md.

Current targeted evidence: 40 JS regressions and 11 focused Python shape tests
passed after the visual update; the broader Phase 5 batch passed 38 focused
Python tests before that visual-only update. The full application suite did not
collect in the minimal environment. No new production camera/session acceptance
is claimed. See GAME_UPDATE_PHASE_5_2026-11-14.md for remaining work.

Working integration Git checkout: ADHD/ULRICH-system. Make future commits here,
or clone its remote; changes in the external October 11 folder do not
automatically synchronize to this checkout. No runtime data, credentials, test
virtual environment or generated screenshot evidence was copied into Git.

The October 17 working changes are still not assumed recovered. The section below
documents the original import, NOT the current version.

## Source provenance — 2026-10-25

This repository starts from the available 2026-10-04 21:23:33 release-staging
source copy. It was selected over NEW SETUP and CLIENT-READY because it includes
the first-login setup service, which those older copies do not contain.

IMPORTANT: This is a recovery baseline, NOT a claim that all previously discussed
fixes have been recovered. The previous Desktop working directory was not present
when this repository was prepared. In particular the October 17 participant
baseline/event journal/reconnect changes and their audit file were not found in
this source copy. Earlier reported test counts must not be attributed to this
repository. Recover and compare that working copy before assuming feature parity.

The original copies have not been deleted or overwritten. Runtime databases,
credentials, participant records, logs, virtual environments, backups and ZIPs
were excluded. Example environment files and model assets remain in source.

## Daily workflow

1. Open this ULRICH-system folder in GitHub Desktop using Add Existing Repository.
2. Fetch/Pull before starting work.
3. Create a focused feature/fix branch (for example codex/camera-recovery).
4. Review changes, test, and commit with a descriptive summary.
5. Push the branch and open a pull request; review before merging to main.

Keep the GitHub repository private. Invite collaborators individually through
Settings > Collaborators; do not share local login keys. Each collaborator should
clone the repository and create their own local environment/database.

Do not commit .env, participant data, raw recordings, exports or backups. Example
configuration files must contain placeholders only. This system collects
behavioral research records; it is not an ADHD diagnosis.

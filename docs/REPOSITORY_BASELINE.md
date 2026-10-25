# Repository baseline and collaboration

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

# Access and Participant Workflow

Last updated: 2026-09-18

## Roles

- **Owner** — the original main-server access key; full local system access.
- **Administrator** — named account management, participant profiles, settings, calibration, sessions, reports, and audit functions.
- **Standard user** — participant preparation, calibration, monitoring, research tasks, and records created under that account. Advanced settings, account management, database backup, and audit endpoints are blocked.

## Named access tokens

The Owner or Administrator opens **Access management**, enters the borrower's name, professional title, organization, permission role, and access duration, then generates a token.

- New accounts use a short six-digit numeric PIN for easier entry on the tablet.
- Owner/Admin can view and copy the PIN from Access management or replace a legacy token with a new PIN.
- A keyed hash is still used for login verification. The visible PIN is stored locally so administrators can retrieve it; therefore the Access management page and database backups must be protected.
- Tokens can expire and can be revoked immediately when the device is returned.
- Disabled accounts invalidate existing signed sessions on the next request.
- Owner/Admin may permanently delete an unused account directly from its account row. Accounts that own participant, session, or calibration records must be revoked instead so the research audit trail remains intact.
- Login audit events record the named user and role.
- Standard users cannot list, open, edit, delete, report, or export participants and sessions owned by another named account. Ownership is enforced by the server, not only hidden in the interface.

The original `RESEARCHER_ACCESS_KEY` remains the Owner recovery credential and must be kept private.

## Participant profile

The dedicated **Participants** page includes:

- participant code and full name;
- date of birth and age group;
- sex and optional gender;
- grade/year and school, clinic, or study site;
- optional address, only when the approved protocol requires it;
- parent/guardian, consent reference, and consent date;
- reported diagnosis status;
- optional medication, accommodations, and research notes.

Existing participant records are preserved. New columns are added automatically when the server starts.

Each participant directory card has its own delete control. The server allows deletion only when no session records are linked to that participant.

## Operator workflow

1. Sign in with the assigned named token.
2. Add or select the participant profile.
3. Confirm consent and relevant accommodations.
4. Complete guided calibration or a quick baseline verification.
5. Start the monitoring session and participant task.
6. Stop and review the result.
7. Sign out and return the device.

## Privacy rules

- Collect exact address only when explicitly required by the approved protocol.
- Prefer participant codes in exported research datasets.
- Do not treat reported diagnosis status as a diagnosis produced by this system.
- Revoke borrower access after device return.
- Keep the Owner key and newly displayed access tokens private.
## Calibration responsibility and frequency

System calibration is attached to the equipment and room, not to a participant. It is completed during the initial setup and repeated only after a relevant equipment, room, lighting, model, or configuration change.

| Level | Who can perform it | When it is required |
|---|---|---|
| System / room calibration | Owner/Admin or authorized device operator | Initial installation, then after camera position, room, lighting, model, or important settings change |
| Automatic session-start check | Application, visible to the operator only when correction is needed | Every time Start session is selected; silently samples live cameras, tracking, framing, measured FPS, and privacy state for two seconds |

The automatic check does not create or replace a participant calibration baseline. In REAL mode the server blocks session creation when the saved system setup is invalid or when the live automatic check fails. A passing or failing automatic result is retained in the audit trail.

The normal Dashboard shows only **Select participant** and **Start session**. If the system setup is invalid, it links the operator to the exact repair step. If live framing fails, it gives one focused correction and lets the operator retry Start session.

For children who may not consistently follow commands, begin with quiet/passive observation. The participant screen asks the child to sit comfortably and look toward the cameras; technical corrections remain on the operator screen.

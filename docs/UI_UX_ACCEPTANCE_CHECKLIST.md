# UI/UX enhancement acceptance checklist

## Later interactive evidence — 3 October 2026

See [WORKFLOW_QA_2026-10-03.md](WORKFLOW_QA_2026-10-03.md) for the isolated browser walkthrough, reproduced defects, corrected behavior and remaining physical/accessibility/download acceptance. The original unchecked items are not all certified by this pass; mock workflow success is not a real-patient/device acceptance result.

## Latest completion evidence

190 isolated tests passed. Authenticated account-role/list/report/export boundaries are now tested, including a corrected reviewer list leak. Thirty-six main-page/viewport combinations passed overflow and visible-input naming checks. Readable labels, additional glossary/error recovery, settings keyboard order and dark settings button contrast received follow-up fixes/checks.

Main server now runs in real mode on port 8000, but the latest backend fix still requires restart: the controlled restart command was blocked. Pi resolution/connectivity, physical tablet/camera tests, actual screen-reader/browser-zoom acceptance and explicit ZIP-build approval remain open. See the completion-pass section of CURRENT_SYSTEM_AUDIT.md; older counts/availability notes below are historical, not current evidence.

## Status separation — updated 3 October 2026

- **Implemented + automated evidence:** activity/practice/report/export matrix (80 combinations), pairing/session ownership regressions, draft handling and shared error formatter. Full suite: 185 tests passed. These are not 185 UI acceptance items.
- **Implemented + limited browser evidence:** operator paired link/QR, adult activity recommendation, readable settings help, participant directory, and existing navigation guards.
- **Verification pending:** rows marked Acceptance pending or carrying limited-evidence notes below. Their implementation mapping does not establish full acceptance.
- **Implementation/coverage review pending:** exhaustive technical-help coverage and failure-message coverage across every screen, plus the whole-application visual review. Expanded shared help/errors do not justify declaring every field/error complete.
- **Blocked by device availability:** actual camera movement/calibration, tablet input and client-router reconnect tests; Pi health timed out at the known hostname/address on this audit.
- **Release held:** client build/ZIP requires user confirmation. Port 8000 refused connection; source has not been deployed into a running main server.

See CURRENT_SYSTEM_AUDIT.md for exact evidence. Previous row statuses below remain deliberately conservative; no physical checks were fabricated to close unchecked rows.

Audit date: 2026-10-02. No new build or ZIP is authorized. This is the original 180-item scope, not a claim that 180 items have passed physical acceptance testing.

Automated evidence: 103 Python tests passed (including 17 isolated workflow regression cases); all JavaScript files passed syntax checks. Current browser audit confirmed room setup needs no participant, future steps remain locked, and incomplete placement disables Continue. Earlier browser evidence: six responsive viewport checks with no horizontal overflow, completed-placement navigation, focus mode and visible footer. Browser viewport checks approximate the available width at 125–150% zoom; they do not replace actual browser zoom testing. See CURRENT_SYSTEM_AUDIT.md for fixes, exclusions and remaining acceptance work.

`Verified` means inspected or exercised in this session. `Acceptance pending` means implementation exists but its full behavior needs operator/device acceptance. The detailed notes take precedence over a general status.

| # | Requirement | Status / note |
|---|---|---|
| 1 | Padak-on ang maximum content width ngadto sa approximately 1450–1550px. | Verified in code/UI checks |
| 2 | Gamita ang 92–94% sa available screen width. | Verified in code/UI checks |
| 3 | Tangtangon ang sobra ka-compressed one-screen layout. | Verified in code/UI checks |
| 4 | Allow natural vertical scrolling kung daghan ang content. | Verified in code/UI checks |
| 5 | Magbutang og desktop two-column layout: | Verified in code/UI checks |
| 6 | Tablet ug small laptop: horizontal steps. | Verified in code/UI checks |
| 7 | Mobile: single-column cards. | Verified in code/UI checks |
| 8 | Keep consistent page margins ug alignment. | Verified in code/UI checks |
| 9 | Reduce unused blank areas. | Acceptance pending — implementation mapped to calibration/task UI |
| 10 | Limit each step ngadto sa usa ka main task. | Acceptance pending — implementation mapped to calibration/task UI |
| 11 | Base text: 16px. | Acceptance pending — implementation mapped to calibration/task UI |
| 12 | Supporting text: minimum 14px. | Acceptance pending — implementation mapped to calibration/task UI |
| 13 | Input labels: 14–15px. | Acceptance pending — implementation mapped to calibration/task UI |
| 14 | Page title: 28–32px. | Acceptance pending — implementation mapped to calibration/task UI |
| 15 | Step title: 22–26px. | Acceptance pending — implementation mapped to calibration/task UI |
| 16 | Status values: 17–20px. | Acceptance pending — implementation mapped to calibration/task UI |
| 17 | Avoid important text below 13px. | Acceptance pending — implementation mapped to calibration/task UI |
| 18 | Increase line height for readability. | Acceptance pending — implementation mapped to calibration/task UI |
| 19 | Use stronger font weight for instructions. | Acceptance pending — implementation mapped to calibration/task UI |
| 20 | Use plain-language labels instead of technical wording. | Acceptance pending — implementation mapped to calibration/task UI |
| 21 | Desktop left-side step navigation. | Verified in code/UI checks |
| 22 | Display all six phases clearly: | Verified in code/UI checks |
| 23 | Current step highlighted cyan/blue. | Verified in code/UI checks |
| 24 | Completed steps marked green with check. | Verified in code/UI checks |
| 25 | Future steps gray/locked. | Verified in code/UI checks |
| 26 | Completed steps clickable. | Verified in code/UI checks |
| 27 | Incomplete future steps cannot be opened accidentally. | Verified in code/UI checks |
| 28 | Show Step X of 6. | Verified in code/UI checks |
| 29 | Show short description under current step. | Acceptance pending — implementation mapped to calibration/task UI |
| 30 | Preserve completed state while moving between steps. | Acceptance pending — implementation mapped to calibration/task UI |
| 31 | Sticky bottom navigation. | Verified in code/UI checks |
| 32 | Large Previous button on the left. | Verified in code/UI checks |
| 33 | Large primary Continue button on the right. | Verified in code/UI checks |
| 34 | Rename Next depending on context: | Verified in code/UI checks |
| 35 | Minimum button height: 44–48px. | Verified in code/UI checks |
| 36 | Minimum button text: 15–16px. | Acceptance pending — implementation mapped to calibration/task UI |
| 37 | Disable Continue until required checks pass. | Verified in code/UI checks |
| 38 | Explain why Continue is disabled. | Verified in code/UI checks |
| 39 | Keyboard-friendly button focus. | Verified in code/UI checks |
| 40 | Optional automatic progression after successful completion. | Acceptance pending — implementation mapped to calibration/task UI |
| 41 | Replace the initial nine-card display with one large status: | Verified in code/UI checks |
| 42 | Add View technical checks. | Verified in code/UI checks |
| 43 | Technical checks appear in collapsible section. | Verified in code/UI checks |
| 44 | Use friendly labels: | Acceptance pending — implementation mapped to calibration/task UI |
| 45 | Keep raw technical values under Advanced details. | Acceptance pending — implementation mapped to calibration/task UI |
| 46 | Show exact fix when a check fails. | Acceptance pending — implementation mapped to calibration/task UI |
| 47 | Add prominent Refresh checks button. | Verified in code/UI checks |
| 48 | Show last refresh time. | Verified in code/UI checks |
| 49 | Avoid color-only status indicators. | Verified in code/UI checks |
| 50 | Add icons and readable text. | Verified in code/UI checks |
| 51 | Increase both previews to at least approximately 480 × 360. | Acceptance pending — implementation mapped to calibration/task UI |
| 52 | Face and Body previews side-by-side on desktop. | Acceptance pending — implementation mapped to calibration/task UI |
| 53 | Stack previews on smaller screens. | Acceptance pending — implementation mapped to calibration/task UI |
| 54 | Add clear labels above each preview. | Acceptance pending — implementation mapped to calibration/task UI |
| 55 | Add full-screen preview option. | Acceptance pending — implementation mapped to calibration/task UI |
| 56 | Add Swap cameras button. | Acceptance pending — implementation mapped to calibration/task UI |
| 57 | Add face oval overlay. | Acceptance pending — implementation mapped to calibration/task UI |
| 58 | Add body silhouette/frame overlay. | Acceptance pending — implementation mapped to calibration/task UI |
| 59 | Add center guidelines. | Acceptance pending — implementation mapped to calibration/task UI |
| 60 | Green preview border when positioning is correct. | Acceptance pending — implementation mapped to calibration/task UI |
| 61 | Yellow border when adjustment is needed. | Acceptance pending — implementation mapped to calibration/task UI |
| 62 | Red border when detection is unusable. | Acceptance pending — implementation mapped to calibration/task UI |
| 63 | Show direct instruction: | Acceptance pending — implementation mapped to calibration/task UI |
| 64 | Large 20–24px checkboxes. | Verified in code/UI checks |
| 65 | Entire checkbox row clickable. | Verified in code/UI checks |
| 66 | Checked rows turn green. | Verified in code/UI checks |
| 67 | Keep five required placement confirmations. | Expanded to nine confirmations (five placement + four comfort checks). |
| 68 | Disable Continue until all five are checked. | All nine confirmations now required. |
| 69 | Larger animated head guide. | Acceptance pending — implementation mapped to calibration/task UI |
| 70 | Larger live face preview. | Acceptance pending — implementation mapped to calibration/task UI |
| 71 | Large central instruction: | Acceptance pending — implementation mapped to calibration/task UI |
| 72 | Show only one instruction at a time. | Acceptance pending — implementation mapped to calibration/task UI |
| 73 | Use countdown ring. | Acceptance pending — implementation mapped to calibration/task UI |
| 74 | Add visible progress: | Acceptance pending — implementation mapped to calibration/task UI |
| 75 | Guided sequence: | Acceptance pending — implementation mapped to calibration/task UI |
| 76 | Voice prompts as optional setting. | Acceptance pending — implementation mapped to calibration/task UI |
| 77 | Add sound cue before movement. | Acceptance pending — implementation mapped to calibration/task UI |
| 78 | Show detected versus expected direction. | Acceptance pending — implementation mapped to calibration/task UI |
| 79 | Add Retry current movement. | Acceptance pending — implementation mapped to calibration/task UI |
| 80 | Do not restart the entire process for one failed direction. | Acceptance pending — implementation mapped to calibration/task UI |
| 81 | Add distance feedback: | Acceptance pending — implementation mapped to calibration/task UI |
| 82 | Smooth distance measurements to prevent flickering. | Acceptance pending — implementation mapped to calibration/task UI |
| 83 | Show success animation after completion. | Acceptance pending — implementation mapped to calibration/task UI |
| 84 | Use friendly language rather than calibration jargon. | Acceptance pending — implementation mapped to calibration/task UI |
| 85 | Larger body preview. | Acceptance pending — implementation mapped to calibration/task UI |
| 86 | Add skeleton overlay option. | Per-preview skeleton/guide toggle implemented; live off/on acceptance remains. |
| 87 | Highlight the detected body region being moved. | Measured-region highlighting implemented; arm groups must be enabled for arm telemetry. |
| 88 | Display one instruction at a time: | Verified in code/UI checks |
| 89 | Use visual animation for each requested movement. | Acceptance pending — implementation mapped to calibration/task UI |
| 90 | Add automatic confirmation when movement is detected. | Heuristic confirmation with manual fallback; actual movement acceptance remains. |
| 91 | Show Detected or Try again. | Acceptance pending — implementation mapped to calibration/task UI |
| 92 | Add manual operator confirmation if automatic detection is uncertain. | Acceptance pending — implementation mapped to calibration/task UI |
| 93 | Display one-participant warning. | Acceptance pending — implementation mapped to calibration/task UI |
| 94 | Warn if required joints leave the frame. | Acceptance pending — implementation mapped to calibration/task UI |
| 95 | Show completion progress. | Verified in code/UI checks |
| 96 | Provide per-movement retry. | Acceptance pending — implementation mapped to calibration/task UI |
| 97 | Hide raw movement values under Advanced details. | Verified in code/UI checks |
| 98 | Separate Practice and Recorded modes visually. | Acceptance pending — implementation mapped to calibration/task UI |
| 99 | Show: | Acceptance pending — implementation mapped to calibration/task UI |
| 100 | Select the participant activity/screen. | Acceptance pending — implementation mapped to calibration/task UI |
| 101 | Automatically recommend an activity based on age. | Age-compatible task and level recommendation; DOB/age data must be correct. |
| 102 | Allow Child, Teen, or Adult profile. | Acceptance pending — implementation mapped to calibration/task UI |
| 103 | Allow Easy, Standard, or Advanced level where appropriate. | Acceptance pending — implementation mapped to calibration/task UI |
| 104 | Show selected participant. | Acceptance pending — implementation mapped to calibration/task UI |
| 105 | Show selected task and trial count. | Acceptance pending — implementation mapped to calibration/task UI |
| 106 | Test keyboard response. | Keyboard practice supported; physical input acceptance remains. |
| 107 | Test tablet/touch response. | Touch practice supported; actual tablet acceptance remains. |
| 108 | Confirm participant understands instructions. | Acceptance pending — implementation mapped to calibration/task UI |
| 109 | Add Open participant screen. | Acceptance pending — implementation mapped to calibration/task UI |
| 110 | Show participant-screen connection state. | Token-authenticated display heartbeat added; reconnect acceptance remains. |
| 111 | Prevent recorded task until practice is complete. | Verified in code/UI checks |
| 112 | Keep participant-facing screen free of researcher settings. | Acceptance pending — implementation mapped to calibration/task UI |
| 113 | Simplify final review to: | Verified in code/UI checks |
| 114 | Add editable profile name. | Acceptance pending — implementation mapped to calibration/task UI |
| 115 | Add optional notes. | Acceptance pending — implementation mapped to calibration/task UI |
| 116 | Show date/time. | Verified in code/UI checks |
| 117 | Show operator name. | Verified in code/UI checks |
| 118 | Show camera/source configuration summary. | Verified in code/UI checks |
| 119 | Hide configuration hash under Advanced details. | Verified in code/UI checks |
| 120 | Provide Save draft. | Verified in code/UI checks |
| 121 | Provide one clear Accept setup primary action. | Verified in code/UI checks |
| 122 | Explain that accepted profiles become locked. | Verified in code/UI checks |
| 123 | Allow deleting draft profiles. | Verified in code/UI checks |
| 124 | Do not allow deleting accepted profiles accidentally. | Verified in code/UI checks |
| 125 | Provide replacement profile workflow after setup changes. | Acceptance pending — implementation mapped to calibration/task UI |
| 126 | Add dedicated success screen: | Verified in code/UI checks |
| 127 | Add short check animation. | Acceptance pending — implementation mapped to calibration/task UI |
| 128 | Add Return to dashboard. | Verified in code/UI checks |
| 129 | Add Select participant. | Acceptance pending — implementation mapped to calibration/task UI |
| 130 | Add Start readiness check. | Verified in code/UI checks |
| 131 | Show when recalibration is next required. | Verified in code/UI checks |
| 132 | Avoid immediately returning without confirmation. | Acceptance pending — implementation mapped to calibration/task UI |
| 133 | Rename Exactly one usable face to One face is clearly visible. | Verified in code/UI checks |
| 134 | Rename Exactly one primary body to One participant is detected. | Verified in code/UI checks |
| 135 | Rename Eye baseline calibrated to Normal eye position saved. | Verified in code/UI checks |
| 136 | Rename Neutral head calibrated to Straight-ahead head position saved. | Verified in code/UI checks |
| 137 | Rename Raw recording disabled to Video is not being saved. | Verified in code/UI checks |
| 138 | Rename Processing FPS to Analysis speed, with technical value under details. | Acceptance pending — implementation mapped to calibration/task UI |
| 139 | Explain technical terms through tooltips. | Core measurement tooltips added; not a glossary for every technical field. |
| 140 | Keep detailed diagnostics accessible but collapsed by default. | Acceptance pending — implementation mapped to calibration/task UI |
| 141 | Every error should include the cause and exact action. | Calibration/actionable errors improved; not every application error has been individually audited. |
| 142 | Example: | Acceptance pending — implementation mapped to calibration/task UI |
| 143 | Add Retry beside failed checks. | Acceptance pending — implementation mapped to calibration/task UI |
| 144 | Add camera reconnection progress. | Connecting/reconnecting state and failed-frame count, not a fabricated progress percentage. |
| 145 | Add network/Pi status indicator. | Acceptance pending — implementation mapped to calibration/task UI |
| 146 | Distinguish temporary connection warning from permanent failure. | Acceptance pending — implementation mapped to calibration/task UI |
| 147 | Preserve completed checks during short connection loss. | Acceptance pending — implementation mapped to calibration/task UI |
| 148 | Warn before abandoning calibration. | Verified in code/UI checks |
| 149 | Add Save and continue later. | Verified in code/UI checks |
| 150 | Resume from the last completed step. | Verified in code/UI checks |
| 151 | Persistent participant summary. | Acceptance pending — implementation mapped to calibration/task UI |
| 152 | Display: | Acceptance pending — implementation mapped to calibration/task UI |
| 153 | Prevent testing the wrong participant. | Acceptance pending — implementation mapped to calibration/task UI |
| 154 | Show No participant selected clearly. | Verified in code/UI checks |
| 155 | Participant data remains isolated by authorized account. | Active-session endpoint now enforces session ownership; full role-matrix acceptance remains. |
| 156 | Avoid exposing unrelated participant records. | Participant/session access restrictions present; comprehensive privacy acceptance remains. |
| 157 | Add confirmation before starting a recorded session. | Verified in code/UI checks |
| 158 | Provide quick participant-switch action before recording. | Acceptance pending — implementation mapped to calibration/task UI |
| 159 | Larger click/touch targets. | Verified in code/UI checks |
| 160 | Visible keyboard focus outlines. | Verified in code/UI checks |
| 161 | Full keyboard navigation. | Acceptance pending — implementation mapped to calibration/task UI |
| 162 | Proper labels for screen readers. | Native controls/status text retained; full screen-reader acceptance remains. |
| 163 | Status icons plus text—not color alone. | Verified in code/UI checks |
| 164 | Higher text/background contrast. | Acceptance pending — implementation mapped to calibration/task UI |
| 165 | Reduced-motion option. | Verified in code/UI checks |
| 166 | Optional voice prompts. | Acceptance pending — implementation mapped to calibration/task UI |
| 167 | Light and dark themes. | Calibration light/dark control added; complete visual theme acceptance remains. |
| 168 | Preserve readable layout at 125–150% browser zoom. | Verified in code/UI checks |
| 169 | Avoid flashing or rapidly changing feedback. | Acceptance pending — implementation mapped to calibration/task UI |
| 170 | Use simple, calm animations. | Acceptance pending — implementation mapped to calibration/task UI |
| 171 | Retain dark navy and cyan brand. | Verified in code/UI checks |
| 172 | Reduce excessive borders. | Acceptance pending — implementation mapped to calibration/task UI |
| 173 | Use shadows and spacing for hierarchy. | Acceptance pending — implementation mapped to calibration/task UI |
| 174 | Use green only for successful states. | Acceptance pending — implementation mapped to calibration/task UI |
| 175 | Use yellow for adjustment/review. | Acceptance pending — implementation mapped to calibration/task UI |
| 176 | Use red only for blocking errors. | Acceptance pending — implementation mapped to calibration/task UI |
| 177 | Add subtle page-step transitions. | Acceptance pending — implementation mapped to calibration/task UI |
| 178 | Add checkmark completion animation. | Acceptance pending — implementation mapped to calibration/task UI |
| 179 | Avoid decorative effects that distract participants. | Acceptance pending — implementation mapped to calibration/task UI |
| 180 | Keep researcher UI professional and participant UI friendly. | Acceptance pending — implementation mapped to calibration/task UI |

## Required final physical acceptance

- Run a complete room calibration with both cameras correctly positioned, accept a replacement profile, then start a monitoring session.
- Complete practice on a paired tablet, verify recording is blocked before practice and resumes only on the correct participant/activity/level.
- Verify arm detection with arm measurement groups enabled; use operator confirmation if uncertain. Test one-person and missing-joint warnings.
- Disconnect/reconnect the Pi network, refresh a participant screen, resume saved calibration, and inspect the exported report.
- Verify light theme, keyboard-only navigation and an actual screen reader. These have not all received full physical acceptance.

Room layout and lighting changes cannot be inferred reliably from configuration alone. The operator must repeat setup after physical changes. Calibration does not establish an ADHD diagnosis.

# Behavior Monitor — Research Console

> **Source synchronization — 2026-11-14:** Updated from the recovered October 11
> Pop the Balloon source, plus local Shape Matching/session/report and practice
> re-entry fixes. This is **not a production-approved release**. Unified operator
> game selection, full application/HTTP tests, tablet acceptance and the client's
> actual dark-balloon complaint remain pending. See
> [current verification checklist](docs/GAME_UPDATE_PHASE_5_2026-11-14.md),
> [visual update](docs/SHAPE_MATCHING_VISUAL_UPDATE_2026-11-14.md), and
> [source provenance](docs/REPOSITORY_BASELINE.md). October 17 fixes are not assumed
> recovered. Historical documentation/test counts below are not current evidence.

## Documentation

For the complete setup sequence, use [`STARTUP_AND_CONNECTION_GUIDE_EN.md`](STARTUP_AND_CONNECTION_GUIDE_EN.md) for English or [`STARTUP_AND_CONNECTION_GUIDE.md`](STARTUP_AND_CONNECTION_GUIDE.md) for Bisaya. The [`docs/DOCUMENTATION_INDEX.md`](docs/DOCUMENTATION_INDEX.md) links the illustrated operations manual, safe credential inventory, physical setup, calibration/validation plan, and Raspberry Pi deployment record.

Research prototype for collecting synchronized, objective behavioral measurements and attention-task performance. It does **not** diagnose ADHD and must not output ADHD probability, positive/negative classification, or treatment advice.

## Current implementation

Phase 1 includes a FastAPI server, SQLite schema initialization, responsive tablet-friendly dashboard, REST health/camera endpoints, WebSocket live updates, and clearly marked synthetic mock data. Phase 2 adds OpenCV USB/network camera inputs, bounded latest-frame capture, MJPEG previews, camera discovery, reconnect handling, and performance status. Phase 3 adds MediaPipe facial/eye landmarks, independent left/right Eye Aspect Ratio, a closed-to-open blink state machine, rolling blink rate, annotated preview, and participant-specific eye calibration. Raw-video recording is off by default.

## Web stack

- FastAPI and Uvicorn
- Server-rendered Jinja2 HTML
- Responsive CSS and plain JavaScript
- WebSockets for live measurements
- SQLAlchemy with SQLite
- Chart.js will be introduced with the real-time timeline phase

This stack avoids a Node.js build requirement and works in current desktop and tablet browsers.

## Windows setup

Install 64-bit Python 3.11 from Python.org and enable **Add Python to PATH**. Then double-click `run_windows.bat` in this directory. On a first-time computer, it runs the local setup automatically, installs dependencies, initializes the database, and creates private login credentials in the local `.env` file. Later launches start the server directly. Alternatively, from PowerShell:

```powershell
.\run_windows.bat
```

Open `http://127.0.0.1:8000` on the laptop. The launch output also prints the LAN address to open on a tablet connected to the same trusted network.

The CLEAN package defaults both camera sources to the Raspberry Pi: `FACE_CAMERA_SOURCE=http://adhd-camera.local:8090/stream/face` and `BODY_CAMERA_SOURCE=http://adhd-camera.local:8090/stream/body`. The Pi must be online on the same private network. If its hostname changes, update both values in the local `.env` and restart. Never include the generated `.env` in a shared ZIP. See `docs/Behavior_Monitor_Startup_and_Raspberry_Pi_Connection_Guide.docx` for the first-time setup and network checks.

## Development modes

The client package defaults to `APP_MODE=real` and the two Raspberry Pi streams. `APP_MODE=mock` is available only for development; generated values are visibly marked **DEMO / MOCK DATA** and must never be treated as real participant measurements.

For local development only, camera sources can instead use direct USB indexes:

```dotenv
FACE_CAMERA_SOURCE=0
BODY_CAMERA_SOURCE=1
```

## Privacy and research safeguards

- Raw-video recording defaults to off.
- No face recognition or biometric identity storage.
- Use participant codes rather than names whenever possible.
- Keep prototype data on the local research network.
- Informed consent or guardian consent and appropriate institutional/ethics approval are required for real participants, especially children.

## Verification

After setup:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Physical-camera verification is intentionally deferred until the camera input phase and suitable hardware are available.

## Phase 2 camera mode

Edit `.env` and set `APP_MODE=real`, then configure `FACE_CAMERA_SOURCE` and `BODY_CAMERA_SOURCE`. Sources may be Windows camera indexes or later Raspberry Pi HTTP/RTSP stream URLs. The server continues running when a source is unavailable and periodically reconnects.

Camera endpoints:

- `GET /api/cameras/status` — state, FPS, latency, failures, and dropped frames
- `GET /api/cameras/discover?max_index=5` — bounded USB camera-index probe
- `GET /preview/face` and `GET /preview/body` — MJPEG browser previews

## Phase 3 face and blink analysis

Real-camera mode runs facial analysis independently at `FACE_PROCESS_FPS`. The dashboard and `GET /api/face/status` expose face-tracking state, left/right/average EAR, open/closed state, blink total, rolling blinks per minute, processing FPS, and the active threshold.

A blink requires at least `MIN_CLOSED_FRAMES` consecutive closed-eye observations followed by reopening. One low-EAR frame is not counted. Thresholds are configurable and must not be interpreted as clinical cutoffs.

To perform participant-specific eye calibration, have the participant sit normally, face the camera, look toward screen center, and keep their eyes naturally open. Then call:

```powershell
Invoke-RestMethod -Method Post "http://127.0.0.1:8000/api/face/calibration/start?duration_seconds=10"
```

The system uses the median observed open-eye EAR to derive a session threshold. Glasses, lighting, camera distance, and face angle can still affect measurements.

## Phase 4 head pose and movement

The face worker estimates numerical yaw, pitch, and roll from stable facial landmarks using OpenCV `solvePnP`. Exponential smoothing reduces landmark jitter. Head-movement events use a configurable magnitude threshold, a lower release threshold (hysteresis), and a refractory period so a held pose is not counted repeatedly.

The dashboard and `GET /api/head/status` expose yaw, pitch, roll, direction, movement magnitude, total movements, movements per minute, and calibration state. Direction labels are descriptive; numerical values remain available.

Before a real session, ask the participant to sit normally and look at screen center, then run:

```powershell
Invoke-RestMethod -Method Post "http://127.0.0.1:8000/api/head/calibration/start?duration_seconds=10"
```

The median pose becomes that session's neutral reference. Head-pose values are approximate camera-relative measurements and are not clinical measurements.

## Phase 5 body pose and movement

The body worker uses the lightweight Ultralytics `yolo11n-pose.pt` model and automatically selects CUDA when a compatible PyTorch/GPU environment is available; otherwise it uses CPU. This computer currently uses the verified CPU fallback. The Raspberry Pi does not run this model.

The worker tracks one primary participant. It initially chooses the largest detected person and then maintains continuity using the nearest normalized bounding-box center when additional people enter the frame. It exposes all 17 COCO body keypoints through the internal analysis pipeline without performing identity recognition.

Body movement is normalized by the visible-body bounding-box diagonal to reduce sensitivity to camera distance. Measurements are separated into head/shoulders, left arm, right arm, torso, left leg, and right leg. Event thresholds use smoothing, hysteresis, and a refractory period. Posture changes use changes in the shoulder-to-hip torso angle.

Use `GET /api/body/status` for tracking state, model/device status, primary subject, regional measurements, movement events, and posture changes. The body preview includes the YOLO skeleton when `SHOW_BODY_SKELETON=true`.

These are descriptive activity measurements, not labels of hyperactivity or clinical fidgeting. Thresholds must be tuned and validated under the approved research protocol.

## Phase 6 participants, sessions, and measurement storage

The dashboard can add and select participant records and start or stop one active monitoring session. Prefer non-identifying codes such as `P001`; display name and age group are optional. Inputs are length-limited and participant codes accept only letters, numbers, underscores, and hyphens.

Every session uses a monotonic clock for comparable elapsed timestamps and UTC wall-clock timestamps for persistent records. Continuous head-pose and body-movement values are sampled once per second only while tracking. Blink, head-movement, body-movement, and posture-change records are event-based. Raw frames are never written to the database.

Stopping a session records its end time, notes, duration, measurement totals, data mode, and final summary. Mock sessions are explicitly stored with `mock_data=true`.

Session endpoints:

- `GET/POST /api/participants`
- `GET /api/sessions`
- `POST /api/sessions/start`
- `POST /api/sessions/{id}/stop`
- `GET /api/sessions/{id}`
- `GET /api/sessions/{id}/summary`

SQLite tables now include participants, sessions, blink events, head-pose samples, head-movement events, body-movement samples/events, posture events, and session summaries. Indexes are present on participant/session identifiers and measurement timestamps.

## Phase 7 Pop the Balloon activity

After a monitoring session starts, open `/attention-task/operator`, pair the participant screen, and complete the five-balloon practice. The participant view contains only the colorful game, goal, progress, and friendly completion/recovery messages—not cameras, tracking errors, technical values, or researcher controls.

The only new-session activity is **Pop the Balloon** (`pop_balloon`, version `2.0.0-balloon`). Easy mode uses **Pop Any Balloon**. Moderate, Hard, and Standard can use **Target Color**, where non-target colors are distractors. Goals are based on correct pops, with presets of 10, 15, 20, and 30 and a custom range of 5–50. The recommended default is 20. Age suggestions are Child 15/Easy, Pre-teen 20/Moderate, Teen 30/Moderate, and Adult 30/Standard; the operator may change them.

Each recorded run saves a random seed and its complete pre-generated sequence. Each balloon saves color, target color, target/distractor status, intended position, size, speed, display/wait timings, UTC and session-relative onset, response time, correctness, missed/false response, premature taps, tracking validity, and pause/reconnect context. Practice uses a separate sequence and is never written as recorded trials.

The game ends automatically at the correct-pop goal, three times the goal in attempts, or the configured time limit (five minutes recommended). Operator pause/resume and early-end reason are supported. A refresh replays only the unfinished planned balloon and cannot duplicate a completed response. Browser `performance.now()` captures the response interval before animation begins.

Saved summaries include the goal, correct/incorrect pops, missed targets, attempts, accuracy, completion state/time, mean/median/variability/min/max reaction time, premature taps, and tracking-quality indicators. Historical task rows from earlier versions remain readable. This activity is a research measurement and must not be described as a validated diagnostic test.

## Phase 8 live timeline and reports

The researcher dashboard includes a local Canvas-based rolling 60-second graph for blink rate, head-pose magnitude, normalized body movement, and attention-task activity. No chart data or browser telemetry is sent to an external CDN or cloud service.

Session History lists saved sessions with participant code, start time, completion state, mode, and a report link. A completed report presents participant/session metadata, duration, blink totals/rate/timeline, head movement and yaw/pitch/roll timeline, body movement and posture events, full attention-task statistics, researcher notes, and the required non-diagnostic disclaimer.

Reports are available as responsive printable pages at `/reports/{session_id}` and structured JSON at `GET /api/reports/{session_id}`. Browser printing may be used to produce an institution-approved PDF if needed; the application does not silently export or upload reports.

## Phase 9 reliability, diagnostics, and LAN security

`GET /api/system/status` reports process uptime/memory, CPU/CUDA selection, package versions, camera statistics, worker state, inference latency, active session, and raw-recording state. Rotating logs are stored locally in `logs/application.log` with a 5 MB limit and three backups; raw frames are never logged.

SQLite uses WAL journaling, foreign-key enforcement, and a five-second busy timeout for safer concurrent camera/session/API writes. Sessions left active by a crash or forced termination are marked `interrupted` on the next startup. An orderly shutdown attempts to finalize the active session with a shutdown note.

API responses include `nosniff`, frame-denial, no-referrer, restrictive browser-permissions, and no-store headers. JSON request bodies larger than 1 MB are rejected. No permissive CORS policy is enabled. Keep the server on a trusted private LAN; do not configure router port forwarding or expose port 8000 directly to the public internet.

Performance controls remain centralized in `.env`: capture resolution/FPS, face/body processing FPS, model confidence, frame dropping, overlays, and analysis thresholds. On this computer PyTorch uses CPU because the installed build does not provide CUDA, even though an NVIDIA MX330 is present. The application remains functional under CPU fallback.

Run validation at any time:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
```

## Phase 10 Raspberry Pi camera node

The Raspberry Pi 4B is a lightweight dual-camera capture and MJPEG streaming node. It does not run MediaPipe, YOLO, the database, sessions, tasks, reports, or the dashboard. Those remain on the Windows main server.

See [`docs/SUPPORTED_HARDWARE_AND_VERSIONS.md`](docs/SUPPORTED_HARDWARE_AND_VERSIONS.md) for the release hardware matrix, camera assignments, model files, version pins, and physical acceptance requirements.

### Raspberry Pi preparation

Use Raspberry Pi OS Bookworm 64-bit, a reliable 5V/3A supply, Ethernet where possible, and two USB webcams. Copy this project to the Pi, then run:

```bash
cd /path/to/adhd-monitoring
chmod +x scripts/setup_raspberry_pi.sh scripts/install_rpi_service.sh
./scripts/setup_raspberry_pi.sh
v4l2-ctl --list-devices
```

Copy `.env.rpi.example` to `.env.rpi` if the setup script has not already done so. Prefer stable camera paths from `/dev/v4l/by-id/` instead of relying permanently on indexes `0` and `1`, because Linux indexes can change after reboot or reconnect:

```dotenv
RPI_HOST=::
RPI_FACE_CAMERA_SOURCE=/dev/v4l/by-id/usb-046d_C505_HD_Webcam_B04D0170-video-index0
RPI_BODY_CAMERA_SOURCE=/dev/v4l/by-id/usb-046d_C505_HD_Webcam_8DACA170-video-index0
RPI_CAMERA_WIDTH=360
RPI_CAMERA_HEIGHT=240
RPI_CAMERA_FPS=30
RPI_JPEG_QUALITY=75
RPI_MOCK_MODE=false
```

Test manually:

```bash
.venv-rpi/bin/python run_rpi_node.py
hostname -I
curl http://127.0.0.1:8090/health
```

From the Windows laptop browser, verify `http://<PI-IP>:8090/health`, `http://<PI-IP>:8090/stream/face`, and `http://<PI-IP>:8090/stream/body`. If a firewall is enabled on the Pi, allow TCP port 8090 only from the trusted local subnet. Do not port-forward this service on the router.

After manual testing, enable automatic startup:

```bash
./scripts/install_rpi_service.sh
sudo systemctl status behavioral-camera-node.service
journalctl -u behavioral-camera-node.service -f
```

### Windows main-server configuration

Copy the relevant values from `.env.windows-rpi.example` into the Windows `.env`, replacing the hostname with the Pi's reserved DHCP address or resolvable hostname:

```dotenv
APP_MODE=real
FACE_CAMERA_SOURCE=http://adhd-camera.local:8090/stream/face
BODY_CAMERA_SOURCE=http://adhd-camera.local:8090/stream/body
SAVE_RAW_VIDEO=false
```

Restart `run_windows.bat`. The existing camera abstraction accepts the network URLs without changes to face, blink, head, YOLO pose, movement, session, or dashboard modules. The main server drops stale frames and reconnects automatically when the Pi or a camera temporarily disconnects.

### Camera-node mock test

The Pi node can be tested without cameras:

```bash
RPI_MOCK_MODE=true .venv-rpi/bin/python run_rpi_node.py
```

The complete network path was verified with both physical Logitech C505 cameras. The Pi reports both sources connected and the outgoing MJPEG frames decode at exactly 360×240 on Windows. The webcams negotiate a physical 320×240 mode at approximately 15 FPS when operating together; 30 FPS is the configured stream target, not a claim of 30 unique physical frames per second. A temporary Windows Main Server validation instance connected to both URLs, reported approximately 16–17 receive FPS with zero failed frames, and kept the YOLO model ready on CPU.

## Phase 11 graphical settings and calibration

Open `/settings` from the dashboard's **Settings & Calibration** link. The page provides validated controls for real/mock mode, USB indexes or Raspberry Pi stream URLs, capture resolution/FPS, processing rates, EAR/blink settings, head smoothing and movement thresholds, YOLO/keypoint confidence, body/posture thresholds, and landmark/skeleton overlays.

USB Camera Discovery scans indexes 0–4. Live diagnostics show CPU/CUDA, memory, uptime, active session, camera state, worker state, inference latency, model readiness, and raw-recording status. Eye and neutral-head calibration can be started directly from the page while the participant is seated normally and facing screen center.

Settings are saved only through an allow-list with type/range validation. An existing `.env` is backed up to `.env.backup` before modification. Configuration changes are rejected while a monitoring session is active and display **restart required** because camera/model workers read settings at startup.

Raw-video recording is deliberately locked off in the prototype UI. It cannot be enabled through the settings API without an approved protocol and code-level change.

## Phase 12 research workspace interface

The main dashboard now uses a persistent research-workspace navigation model with dedicated anchors for Overview, Participants, Active Session, Attention Task, Timeline, and Session History. Settings & Calibration remains a separate administrative page, while the participant task remains visually isolated from researcher measurements.

The top bar shows connection and operating mode. Overview cards summarize both camera inputs, AI device, and active-session state. Monitoring cards preserve all numerical data while presenting camera, performance, face/head, body/posture, task, and event-timeline information in a clearer hierarchy.

The layout adapts from a two-camera desktop workspace to a single-column tablet view. On narrower screens the sidebar becomes a menu drawer. Keyboard focus styles, semantic headings, descriptive preview alt text, scalable typography, and horizontally scrollable data tables improve accessibility without adding external UI dependencies.

## Phase 13 hardware validation and commissioning

Open `/hardware` or choose **Hardware Validation** in the sidebar. This page performs live, read-only readiness checks for real-camera mode, both camera connections, capture FPS, the Face AI worker, YOLO Pose model readiness, and the raw-recording privacy lock. It also identifies whether the configured topology is direct USB or Raspberry Pi network streaming and lists the physical tests that cannot be proven by automated software alone.

Run the Windows validation from the project directory while the main server is running:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\test_hardware.ps1
```

On the Raspberry Pi, run:

```bash
chmod +x scripts/test_rpi_hardware.sh
./scripts/test_rpi_hardware.sh
```

The first real-laptop commissioning run on 2026-09-16 passed 5 of 8 automatic checks. Camera 0 connected and the face worker, YOLO Pose model, real mode, and privacy lock were operational. Camera 1 was unavailable, so body connectivity and body FPS failed; camera 0 measured approximately 8 FPS, below the 10 FPS readiness target. This is an honest hardware blocker, not a software test failure.

Before marking Phase 13 complete, connect both webcams to the Raspberry Pi, configure the Windows sources as `http://<PI-IP>:8090/stream/face` and `http://<PI-IP>:8090/stream/body`, and verify all of the following: simultaneous capture, participant framing and calibration, camera unplug/reconnect, network interruption recovery, Pi reboot/autostart, sustained Ethernet throughput, and acceptable Pi temperature. The validation script exits with a nonzero status until all eight automatic checks pass.

## Phase 14 research data export and backup

Each session report now provides **Export JSON** and **Export CSV package** actions. JSON is suitable for programmatic analysis. The ZIP research package contains the complete JSON report plus separate CSV files for blinks, head pose, head movements, body samples, body movements, posture events, and attention trials. Its `manifest.json` records schema version, export time, participant code, file sizes, and a SHA-256 checksum for every file.

API endpoints:

```text
GET /api/exports/sessions/<session-id>.json
GET /api/exports/sessions/<session-id>.zip
GET /api/exports/database-backup.zip
```

The database endpoint uses SQLite's online backup mechanism, so it creates a consistent snapshot even while the application is running. The backup ZIP includes its own SHA-256 manifest. Exports contain research identifiers and must be stored securely. No export includes raw camera video, and raw-video recording remains locked off.

Automated tests now use a unique temporary SQLite database, preventing test participants and sessions from entering the real research database.

## Phase 15 local access control and audit trail

Researcher pages, APIs, camera previews, exports, and the monitoring WebSocket now require the local access key configured in `.env`. Successful login issues a signed, HttpOnly, SameSite=Strict cookie that expires after `AUTH_SESSION_HOURS`; the dashboard includes a **Sign out** action. `/api/health` and static login assets remain public so the server can be checked without exposing research records.

When `run.py` starts, its terminal banner shows whether researcher login is enabled and displays the configured local access key. The redesigned login screen also includes a collapsible **Where can I find the access key?** guide. If port 8000 is already occupied by this application, `run.py` now reports that the server is already running instead of continuing into a socket-bind traceback; use the displayed URL or close the existing server before starting another copy.

```dotenv
AUTH_ENABLED=true
RESEARCHER_ACCESS_KEY=<private local key>
SESSION_SECRET=<at least 32 random characters>
AUTH_SESSION_HOURS=8
```

Do not commit or share the actual `.env`. Change the access key before deployment if it may have been disclosed. The supported client deployment is an **isolated, trusted local D-Link LAN with no port-forwarding or public exposure**. Because the local prototype uses plain HTTP, the cookie is not marked Secure. If the system must cross an untrusted network, place it behind an HTTPS reverse proxy, enable Secure cookies, and complete a security review before collecting participant data.

Audit events are available to authenticated researchers at `GET /api/audit?limit=100`. The database records successful and failed login attempts, participant creation, session start/stop, settings updates, session exports, and database backups. Audit entries contain action, timestamp, optional record identifier, client IP, result, and limited details; they never contain the access key, raw frames, or raw video.

## Compact professional dashboard redesign

The main dashboard is now a dense research console rather than a presentation-style card layout. A narrow sidebar separates Overview, Live Monitor, Attention Task, and Records. The overview uses a single status strip and compact session control bar. Participant management, camera technical details, regional body metrics, and the signal timeline use native expandable groups so secondary information stays out of the way until needed.

The camera layout dropdown switches among both cameras, face only, body only, and metrics only. Common live indicators are prioritized beside each feed, while capture FPS, latency, dropped frames, EAR, pose angles, and regional movement are grouped under technical details.

Session records have a status filter and a per-row Actions dropdown with Open Report, Export Data, and Delete Session. Deletion requires an explicit browser confirmation and server-side `confirm=true`; active sessions cannot be deleted. Participant deletion is available inside the participant-management group but is allowed only after that participant's sessions have been removed. All successful deletions are written to the audit trail.

The application shell now supports a persistent collapsible sidebar and persistent light/dark themes. On desktop the menu collapses to a 64-pixel icon rail, preserving navigation tooltips while giving the camera workspace more room. On smaller screens it continues to behave as an off-canvas drawer. Both preferences are saved locally in the browser; the initial theme follows the operating-system preference when no choice has been saved.

The top-right System menu is a structured maintenance panel with distinct Settings & Calibration, Hardware Validation, and Database Backup actions, each with a short purpose description. Its surface, typography, controls, live indicators, charts, tables, feeds, and focus treatment have matching light and dark tokens.

## Attention-task participant workflow redesign

The participant task now begins with a distraction-limited instruction and readiness screen. It presents Star/Respond and Circle/Do Not Respond as visual rules, verifies the local server and active monitoring session, displays the configured recorded-trial count, and disables the recorded task until a session exists. A four-example practice mode uses the same keyboard/touch response interaction but never calls the trial API and therefore does not enter practice data in the research database.

The recorded task uses a fullscreen countdown, randomized fixation interval, minimal progress display, keyboard Space response, and a large tablet-friendly response button. Correctness feedback is intentionally omitted during recorded trials. Pause is allowed safely between stimuli; ending a task requires confirmation, removes only an unfinished active trial, preserves completed trials, and writes an audit event. A dedicated connection-interruption state prevents the page from silently continuing after an API failure.

The completion screen confirms recording without presenting a diagnostic or performance interpretation to the participant. The page uses the dashboard's persistent light/dark theme preference and includes a theme toggle, responsive layout, visible focus states, semantic status text, and shape-based—not color-only—instructions.

## Landmark and feature profiles

Settings & Calibration includes a lightweight Landmark & Feature Profile editor. Presets are **Core Monitoring**, **Upper Body**, and **Full Body**; selecting or clearing an individual option switches the profile to **Custom**. Face and body groups have independent Display and Measure columns. Display controls overlays, while Measure determines which synchronized samples/events are written to a session.

Face groups are Eyes, Iris, Head Pose, Mouth, and Face Contour. Body groups are Head/Shoulders, Left Arm, Right Arm, Torso/Hips, Left Leg, and Right Leg. Derived feature switches cover Position, Distance, Angle, Velocity, Movement Frequency, and Normalized Movement. Server validation rejects unknown groups, an empty measurement configuration, angle configurations without a compatible group, and normalized movement without a body group.

The implementation remains lightweight: MediaPipe and YOLO each still run a single inference pass. Selection changes overlay drawing, regional post-processing, and database persistence rather than spawning additional models. Changes are locked while a monitoring session is active and require the normal server restart after saving.

Every completed session stores schema version `landmarks-1.0`, profile, sorted display/measure groups, feature types, fixed-order/availability-mask declarations, and a deterministic configuration hash in its summary and research export. This makes sessions reproducible without claiming that an untrained temporal model already exists.

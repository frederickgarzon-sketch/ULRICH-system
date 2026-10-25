# Supported hardware, assignments, and software versions

Release reference: 2026-10-03

This is the supported configuration for the current research-console release. Devices outside this matrix may work, but must pass the six-step setup and an actual-device acceptance test before use.

## Main server

- Windows 10 or Windows 11, 64-bit.
- Python 3.11, 64-bit.
- CPU operation is supported. A compatible CUDA GPU is optional and is selected automatically by Ultralytics when available.
- The Windows computer runs the dashboard, database, MediaPipe face analysis, YOLO pose analysis, tasks, exports, and reports.
- The database is local SQLite by default: `data/behavioral_monitoring.db`.

## Camera configurations

### Two local USB cameras

- Two UVC-compatible webcams that Windows and OpenCV can open independently.
- Face source: normally camera index `0`.
- Body source: normally camera index `1`.
- The setup wizard must confirm that the assignments are not identical; indexes can be swapped when Windows enumerates them differently.
- Configured capture target: 640×480 at 20 FPS per camera.
- Processing target: face 15 FPS; body 10 FPS.
- Acceptance minimums shown by calibration: face at least 10 measured FPS; body at least 8 measured FPS.

### Raspberry Pi camera node

- Raspberry Pi 4B with Raspberry Pi OS 64-bit, two independently accessible UVC USB webcams, and a stable 5 V / 3 A power supply.
- Default hostname: `adhd-camera.local`.
- Face stream: `http://adhd-camera.local:8090/stream/face`.
- Body stream: `http://adhd-camera.local:8090/stream/body`.
- Health endpoint: `http://adhd-camera.local:8090/health`.
- The Pi is a capture/streaming node only. It does not run the Windows server, database, MediaPipe, YOLO, tasks, or reports in this release.
- Raspberry Pi, Windows server, and participant tablet must use the same trusted local D-Link router/network. HTTP is supported only on an isolated trusted LAN with no Internet port forwarding.

## Models and pinned vision packages

- Pose model: `models/yolo11n-pose.pt` (6,255,593 bytes; SHA-256 `869e83fcdffdc7371fa4e34cd8e51c838cc729571d1635e5141e3075e9319dc0`). Verify this hash before a controlled release.
- OpenCV: `opencv-contrib-python==4.11.0.86`.
- MediaPipe: `mediapipe==0.10.21`.
- Ultralytics: `ultralytics==8.4.153`.
- Other supported dependency ranges are defined in `requirements.txt`; the setup wizard reports the installed versions.

## Physical placement requirements

- Face view: exactly one usable face, both eyes visible, even lighting, and approximately 35–45 cm face distance.
- Body view: exactly one primary participant with all required joints visible for the selected measurement profile.
- Run eye baseline, neutral-head calibration, and UP → DOWN → LEFT → RIGHT → CENTER after moving a camera, changing lighting or furniture, changing sources, or losing saved calibration.
- Raw recording remains off by default. Only derived measurements and research/session records are stored unless the owner deliberately changes the privacy configuration.

## Release acceptance

Passing automated tests does not certify a physical device. Each final installation must complete the setup wizard, participant-screen heartbeat test, one real end-to-end session, exports, and backup/restore smoke test. The application is a research support tool and must not be described as a clinical diagnosis system.

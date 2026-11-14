# Behavior Monitor first time setup on Windows

This package is **copy-and-run after one automatic setup**. It is not a standalone executable: a new computer still needs Python 3.11 (64-bit), internet access for the first dependency install, and the camera or Raspberry Pi devices used at the site. Later launches use the local installation and normally work offline.

## Start on a new computer

1. Extract the complete ZIP to a normal folder, such as `Documents\Behavior-Monitor-Research-Console-CLEAN`. Do not run it from inside the ZIP.
2. Double-click `run_windows.bat`. The first launch creates `.venv`, installs the required Python packages, creates a private `.env`, and initializes a blank local database. This can take several minutes.
3. If prompted by Windows Firewall, allow access on **Private networks** only when other devices on your trusted local network need to connect. Do not expose port 8000 to the internet.
4. Keep the black server window open. The login page opens automatically in the default browser. If it does not, open `http://127.0.0.1:8000/login`. The owner access key appears in the server window. Keep it private.
5. After the first valid owner login, follow the six-step **Initial System Setup** wizard. It checks the application, connects and assigns the cameras, confirms room placement, completes calibration, and tests the participant-screen address. Progress is saved in the local database, so a refresh or restart resumes at the saved step.
6. If camera sources are changed, restart the BAT when the wizard asks. Sign in again and it will return to the saved step.
7. After **Save and finish**, future logins open the simplified Operation Dashboard: select participant → start session. Start session silently checks live camera connection, tracking, framing, measured FPS, and privacy state for two seconds; there is no second manual calibration screen.
8. Technical controls are hidden under **System Setup** and require the owner/admin access key again before cameras, calibration, network, diagnostics, or saved setup can be changed.
9. For the next launch, double-click the same BAT file. It checks the local environment and starts the server without reinstalling packages when they are healthy.

## First recorded participant activity

After the one-time setup is accepted, select the participant and start the monitoring session from Overview. Open **Pop the Balloon**, create the secure participant-screen link/QR, and open that link on the tablet. Do not type `/attention-task` manually because an unpaired screen has no participant capability token.

Run the five-balloon practice first. Practice is not recorded. Confirm the selected age profile, difficulty, mode, target color when applicable, and correct-pop goal; then choose **Begin recorded game**. The game completes automatically at the correct-pop goal. Finish the monitoring session afterward to finalize its report and exports.

## If the first launch stops

- **Python 3.11 not found:** Install 64-bit Python 3.11 from `https://www.python.org/downloads/`. Select **Add python.exe to PATH** during installation. Close and reopen the BAT file.
- **Package installation fails:** Check internet access and free disk space, then run the BAT again. A restricted network may require an administrator to allow Python package downloads.
- **Port 8000 is already in use:** Another copy may already be running. Close its server window with `Ctrl+C`, then launch this copy again. Do not assume a browser tab belongs to the new copy.
- **Browser shows Request origin is not allowed:** Close the older server first, start this package, and use exactly `http://127.0.0.1:8000/login` on the server computer. Avoid mixing `localhost`, LAN IP, and `127.0.0.1` in the same session.
- **Camera or Pi unavailable:** The web server can still open, but hardware-dependent functions need the devices connected and configured.

## Raspberry Pi check

The included defaults are `http://adhd-camera.local:8090/stream/face` and `http://adhd-camera.local:8090/stream/body`. On the Windows computer, open PowerShell and run `ping adhd-camera.local`, then `Test-NetConnection adhd-camera.local -Port 8090`. If the name does not resolve, check that the computer and Pi are on the same network and use the Pi's fixed LAN IP in both `FACE_CAMERA_SOURCE` and `BODY_CAMERA_SOURCE` inside `.env`. Restart the BAT after editing `.env`. A ping reply alone does not prove the streams are working; check both Pi stream endpoints as well.

## Moving or sharing the package

Share the original ZIP or source folder **without** `.env`, `.venv`, or `data` if the next computer must start clean. The package ZIP already excludes local secrets and databases. Do not copy the working `.env` from the first computer: it contains private login credentials. Each computer generates its own key. If you need to move real participant records, use an approved backup and transfer procedure instead of treating the source ZIP as a data backup.

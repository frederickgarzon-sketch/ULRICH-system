@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -c "import fastapi, uvicorn, sqlalchemy, cv2, mediapipe, torch, ultralytics" >nul 2>&1
) else (
  set "NEEDS_SETUP=1"
)
if errorlevel 1 set "NEEDS_SETUP=1"
if defined NEEDS_SETUP (
  echo Preparing this computer for the Behavior Monitor...
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_windows.ps1"
  if errorlevel 1 (
    echo Setup did not complete. Open FIRST_TIME_SETUP.md for help.
    pause
    exit /b 1
  )
)
".venv\Scripts\python.exe" scripts\ensure_local_env.py
if errorlevel 1 (
  echo Local configuration could not be prepared.
  pause
  exit /b 1
)
set "OPEN_LOCAL_BROWSER=1"
".venv\Scripts\python.exe" run.py
set "SERVER_EXIT_CODE=%ERRORLEVEL%"
echo.
if not "%SERVER_EXIT_CODE%"=="0" (
  echo The server stopped unexpectedly or could not start.
  echo Review the final traceback above for the actual cause.
  echo Missing modules or dependencies must be corrected before camera checks can run.
) else (
  echo The server was stopped normally.
)
echo Press any key to close this window.
pause >nul
exit /b %SERVER_EXIT_CODE%

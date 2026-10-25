$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

$PythonExe = $null
$PythonArgs = @()
$Launcher = Get-Command py -ErrorAction SilentlyContinue
if ($Launcher) {
    $PythonCheckOk = $false
    try {
        & $Launcher.Source -3.11 -c "import sys, struct; assert sys.version_info[:2] == (3, 11) and struct.calcsize('P') == 8" 2>$null
        $PythonCheckOk = $LASTEXITCODE -eq 0
    } catch { }
    if ($PythonCheckOk) {
        $PythonExe = $Launcher.Source
        $PythonArgs = @("-3.11")
    }
}
if (-not $PythonExe) {
    $PythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($PythonCommand) {
        $PythonCheckOk = $false
        try {
            & $PythonCommand.Source -c "import sys, struct; assert sys.version_info[:2] == (3, 11) and struct.calcsize('P') == 8" 2>$null
            $PythonCheckOk = $LASTEXITCODE -eq 0
        } catch { }
        if ($PythonCheckOk) { $PythonExe = $PythonCommand.Source }
    }
}
if (-not $PythonExe) {
    Write-Host ""
    Write-Host "Python 3.11 (64-bit) is required but was not found." -ForegroundColor Yellow
    Write-Host "Install Python 3.11 (64-bit) from https://www.python.org/downloads/"
    Write-Host "Enable 'Add python.exe to PATH', then double-click run_windows.bat again."
    exit 1
}

Write-Host "Creating a local Python environment..."
& $PythonExe @PythonArgs -m venv --clear .venv
if ($LASTEXITCODE -ne 0) {
    throw "Could not create the Python environment. Install Python 3.11 (64-bit) and retry."
}

$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
& $VenvPython -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "Could not install requirements. Check internet access and free disk space, then retry." }

New-Item -ItemType Directory -Force -Path (Join-Path $ProjectRoot "data") | Out-Null
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
}

& $VenvPython (Join-Path $ProjectRoot "scripts\ensure_local_env.py")
if ($LASTEXITCODE -ne 0) {
    throw "Local configuration setup failed."
}

& $VenvPython -c "from app.database.database import initialize_database; initialize_database(); print('Database initialized.')"
if ($LASTEXITCODE -ne 0) { throw "Could not initialize the local database." }
Write-Host ""
Write-Host "Setup complete." -ForegroundColor Green
Write-Host "Run: .\run_windows.bat"

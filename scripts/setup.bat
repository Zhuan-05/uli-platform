@echo off
REM ULI Platform - Windows setup. Creates a venv, installs Python deps, builds the UI.
setlocal
cd /d "%~dp0\.."
echo === ULI Platform setup ===

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python 3.11+ not found on PATH. Install from https://www.python.org/downloads/
  exit /b 1
)
where node >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Node.js 18+ not found on PATH. Install from https://nodejs.org/
  exit /b 1
)

if not exist .venv (
  echo [1/4] Creating virtual environment...
  python -m venv .venv || exit /b 1
) else (
  echo [1/4] Reusing existing .venv
)

call .venv\Scripts\activate.bat

echo [2/4] Installing Python dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt || exit /b 1

echo [3/4] Installing frontend dependencies...
pushd frontend
if not exist node_modules (
  call npm install --no-audit --no-fund || (popd & exit /b 1)
) else (
  echo       node_modules present
)

echo [4/4] Building frontend...
call npm run build || (popd & exit /b 1)
popd

echo.
echo Setup complete. Start the platform with: scripts\run.bat
endlocal

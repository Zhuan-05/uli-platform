@echo off
REM ULI Platform - Windows dev launcher (backend only; use npm run dev in frontend\ separately).
setlocal
cd /d "%~dp0\.."
if not exist .venv\Scripts\python.exe (
  echo [ERROR] Run scripts\setup.bat first.
  exit /b 1
)
if "%ULI_CORE_PORT%"=="" set ULI_CORE_PORT=8787
set ULI_CORE_HOST=127.0.0.1
set ULI_CORE_URL=http://127.0.0.1:%ULI_CORE_PORT%
.venv\Scripts\python.exe scripts\run.py --seed --reload
endlocal

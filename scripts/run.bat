@echo off
REM ULI Platform - Windows launcher. Serves Core + UI and registers the example apps.
setlocal
cd /d "%~dp0\.."

if not exist .venv\Scripts\python.exe (
  echo [ERROR] Virtual environment missing. Run scripts\setup.bat first.
  exit /b 1
)

if "%ULI_CORE_PORT%"=="" set ULI_CORE_PORT=8787
set ULI_CORE_HOST=127.0.0.1
set ULI_CORE_URL=http://127.0.0.1:%ULI_CORE_PORT%
set ULI_ENV=production

echo Starting ULI Core on http://%ULI_CORE_HOST%:%ULI_CORE_PORT%
echo UI:  http://%ULI_CORE_HOST%:%ULI_CORE_PORT%/ui/
echo API: http://%ULI_CORE_HOST%:%ULI_CORE_PORT%/docs
echo.
.venv\Scripts\python.exe scripts\run.py --seed --seed-static %*
endlocal

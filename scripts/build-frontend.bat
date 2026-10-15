@echo off
REM Rebuild the ULI web UI into frontend\dist
setlocal
cd /d "%~dp0\..\frontend"
if not exist node_modules call npm install --no-audit --no-fund
call npm run build
echo UI built into frontend\dist
endlocal

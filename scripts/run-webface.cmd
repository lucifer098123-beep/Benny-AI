@echo off
REM ============================================================
REM  Benny webface launcher
REM  Boots the local browser face (localhost-only, private),
REM  waits until the server answers /health, THEN opens the tab.
REM  (Fixes the old race: browser used to open before benny
REM   was breathing -> "127.0.0.1 refused to connect".)
REM ============================================================
setlocal
cd /d "%~dp0.."

start "benny webface" cmd /k "python -m webface"

REM poll until the server is up (max ~30 attempts, 500ms apart)
set /a try=0
:loop
set /a try+=1
if %try% gtr 30 goto giveup
powershell -NoProfile -Command "try{$r=Invoke-WebRequest -Uri 'http://127.0.0.1:7749/health' -TimeoutSec 2 -UseBasicParsing; if($r.StatusCode -eq 200){exit 0}}catch{}exit 1" >nul 2>&1
if %errorlevel%==0 goto up
timeout /t 1 /nobreak >nul
goto loop
:up
start "" http://127.0.0.1:7749
echo.
echo  benny webface is live - http://127.0.0.1:7749
exit /b 0
:giveup
echo  benny webface did not answer /health in time. check the terminal window.
exit /b 1
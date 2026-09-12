@echo off
REM ============================================================
REM  Benny webface launcher
REM  Boots the local browser face (localhost-only, private)
REM  and opens it in the default browser.
REM ============================================================
setlocal
cd /d "%~dp0.."

REM give the server a beat before opening the tab
start "" http://127.0.0.1:7749
python -m webface
exit /b 0
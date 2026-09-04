@echo off
REM ============================================================
REM  Benny auto-push script (triggered on file change)
REM  Pushes ONLY source the agent needs to run.
REM  Never pushes: data/, keys, secrets, API tokens, env files.
REM
REM  Layered safety:
REM    1. .gitignore keeps data/secrets/keys out of tracking.
REM    2. This script scans the staged diff (excluding itself)
REM       for real secret values and BLOCKS the push on a hit.
REM    3. Only currently-tracked files are ever pushed.
REM ============================================================
setlocal
cd /d "%~dp0"

REM ---------- Stage everything tracked/untracked ----------
git add -A
if errorlevel 1 (
    echo [benny] git add failed. Aborting.
    exit /b 1
)

REM ---------- Nothing staged? done. ----------
git diff --cached --quiet
if not errorlevel 1 (
    echo [benny] nothing to push - working tree is clean.
    exit /b 0
)

REM ---------- Scan staged files (skip this script + binary) ----------
echo [benny] scanning staged changes for secret values...

SET SCANOVER="%TEMP%\benny_scan.txt"
SET VIOLATION=0
git diff --cached --name-only --diff-filter=ACMR > "%TEMP%\benny_files.txt"

setlocal enabledelayedexpansion
for /f "usebackq delims=" %%F in ("%TEMP%\benny_files.txt") do (
    if /I not "%%F"=="scripts/auto-push.cmd" (
        echo scanning %%F...
        git show :%%F > "%SCANOVER%" 2>nul
        findstr /r /c:"AIza[0-9A-Za-z_-]" /c:"sk-[A-Za-z0-9]" /c:"eyJ[A-Za-z0-9._-]" /c:"-----BEGIN" /c:"AKIA[0-9A-Z]" /c:"[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]" "%SCANOVER%" >nul
        if not errorlevel 1 (
            echo.
            echo [benny] !!! Possible secret VALUE found in %%F
            echo [benny] EXITING without pushing. Keep secrets local.
            set VIOLATION=1
        )
    )
)
endlocal & set VIOLATION=%VIOLATION%

del "%TEMP%\benny_files.txt" 2>nul
del "%SCANOVER%" 2>nul

if "%VIOLATION%"=="1" exit /b 1

REM ---------- Commit + push ----------
git commit -m "auto: sync source to GitHub" >nul
echo [benny] committed.
git push
if errorlevel 1 (
    echo [benny] push failed.
    exit /b 1
)
echo [benny] pushed to origin/main. Source only. Secrets stayed local.
exit /b 0

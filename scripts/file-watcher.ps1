# ============================================================
#  Benny auto-push watcher (invisible)
#  Polls the repo every N seconds; if there are source changes,
#  runs scripts/auto-push.cmd (which commits + pushes, no-op
#  when clean). Runs hidden. Designed to be launched by a
#  Windows scheduled task at logon.
#
#  Reliability: polling beats FileSystemWatcher for a long-lived
#  background task (no listener leaks, no debounce races).
# ============================================================
param(
    [int]$IntervalSeconds = 15,
    [int]$MaxRuns = -1   # -1 = run forever
)

$RepoRoot = Split-Path -Parent $PSScriptRoot
$PushScript = Join-Path $RepoRoot "scripts\auto-push.cmd"
$LogDir = Join-Path $RepoRoot "data\logs"
New-Item -ItemType Directory -Force -Path $LogDir -ErrorAction SilentlyContinue | Out-Null
$LogFile = Join-Path $LogDir "autopush_watcher.log"
$LastPoll = Join-Path $LogDir ".autopush_last"

# ignore changes that come from the git dir itself
$GitDir = Join-Path $RepoRoot ".git"

function Write-Log($msg) {
    $line = "{0} {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $msg
    Add-Content -LiteralPath $LogFile -Value $line -ErrorAction SilentlyContinue
}

Write-Log "watcher started (interval ${IntervalSeconds}s, maxruns ${MaxRuns})"

$runs = 0
while ($true) {
    # only push if there are actual source changes (ignores .git, data/)
    $status = git -C $RepoRoot status --porcelain 2>$null
    if ($status) {
        Write-Log "change detected; running auto-push"
        & $PushScript *>> $LogFile
    }
    $runs++
    if ($MaxRuns -gt 0 -and $runs -ge $MaxRuns) { break }
    Start-Sleep -Seconds $IntervalSeconds
}
Write-Log "watcher stopped (ran $runs polls)"

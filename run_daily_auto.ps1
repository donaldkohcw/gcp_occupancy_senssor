# ===== run_daily_auto.ps1 =====
# Scheduled entry point for the daily occupancy pipeline. Runs:
#   1) combine_daily.py            (no args -> auto-downloads/combines yesterday + today)
#   2) run_process_all_users.py    (yesterday's folder only)
# Today's folder is intentionally NOT processed/plotted here: sensors keep
# appending to today's log until tomorrow morning, so a plot made today
# would only show a partial day and get silently redone tomorrow anyway.
# Folder numbers are derived from the date using the same BASE_FOLDER_NUM/BASE_DATE
# mapping combine_daily.py and run_process_all_users.py use internally, so this
# script never needs manual folder numbers updated.

$ErrorActionPreference = "Stop"

# Scheduled tasks run under a console codepage (cp1252) that can't encode
# characters like the arrow used in process.py's status prints; without this,
# run_process_all_users.py crashes on the first non-ASCII print and every
# plot after that point in the run never gets generated.
$env:PYTHONIOENCODING = "utf-8"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonExe = "C:\Users\donaldk\scoop\apps\python313\current\python.exe"
$Log       = Join-Path $ScriptDir "run_daily_auto.log"

$BaseFolderNum = 20402
$BaseDate      = Get-Date "2025-11-10"

function Get-FolderNumber($date) {
    $offset = ($date.Date - $BaseDate.Date).Days
    return $BaseFolderNum + $offset
}

Add-Content $Log "`n===== Task started at $(Get-Date -Format 'dd/MM/yyyy HH:mm:ss') ====="

# Each step below uses "*>> $Log" only (no "2>&1"). Combining the two on a
# native exe makes PowerShell wrap stderr lines (e.g. a Python traceback)
# into ErrorRecords, which $ErrorActionPreference="Stop" then promotes into
# a terminating error -- previously, one user's crash silently aborted the
# whole task, skipping every folder/user after it. Each step is also its
# own try/catch so one failure doesn't stop the remaining steps.

try {
    Add-Content $Log "`n--- combine_daily.py (yesterday + today) ---"
    & $PythonExe (Join-Path $ScriptDir "combine_daily.py") *>> $Log
    Add-Content $Log "combine_daily.py exit code: $LASTEXITCODE"
}
catch {
    Add-Content $Log "[ERROR] combine_daily.py: $_"
}

$yesterday       = (Get-Date).AddDays(-1)
$folderYesterday = Get-FolderNumber $yesterday

try {
    Add-Content $Log "`n--- run_process_all_users.py --$folderYesterday ---"
    & $PythonExe (Join-Path $ScriptDir "run_process_all_users.py") "--$folderYesterday" *>> $Log
    Add-Content $Log "run_process_all_users.py --$folderYesterday exit code: $LASTEXITCODE"
}
catch {
    Add-Content $Log "[ERROR] run_process_all_users.py --$folderYesterday`: $_"
}

Add-Content $Log "`n===== Task ended at $(Get-Date -Format 'dd/MM/yyyy HH:mm:ss') ====="

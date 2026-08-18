# ===== run_daily_auto.ps1 =====
# Scheduled entry point for the daily occupancy pipeline. Runs:
#   1) combine_daily.py            (no args -> auto-downloads/combines yesterday + today)
#   2) run_process_all_users.py    (once per folder number, for yesterday and today)
# Folder numbers are derived from the date using the same BASE_FOLDER_NUM/BASE_DATE
# mapping combine_daily.py and run_process_all_users.py use internally, so this
# script never needs manual folder numbers updated.

$ErrorActionPreference = "Stop"

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

try {
    Add-Content $Log "`n--- combine_daily.py (yesterday + today) ---"
    & $PythonExe (Join-Path $ScriptDir "combine_daily.py") *>> $Log 2>&1
    Add-Content $Log "combine_daily.py exit code: $LASTEXITCODE"

    $today           = Get-Date
    $yesterday       = $today.AddDays(-1)
    $folderYesterday = Get-FolderNumber $yesterday
    $folderToday     = Get-FolderNumber $today

    foreach ($folder in @($folderYesterday, $folderToday)) {
        Add-Content $Log "`n--- run_process_all_users.py --$folder ---"
        & $PythonExe (Join-Path $ScriptDir "run_process_all_users.py") "--$folder" *>> $Log 2>&1
        Add-Content $Log "run_process_all_users.py --$folder exit code: $LASTEXITCODE"
    }
}
catch {
    Add-Content $Log "[ERROR] $_"
}

Add-Content $Log "`n===== Task ended at $(Get-Date -Format 'dd/MM/yyyy HH:mm:ss') ====="

# ===== run_combine.ps1 =====

# Disable buffering so logs are written live
#$env:PYTHONUNBUFFERED = "1"

# Paths
$PythonExe = "C:\Users\donaldK\AppData\Local\Programs\Python\Python311\python.exe"
$Script    = "C:\Users\donaldk\work\GCP_service_occupancy_logs\combine_daily.py"
$Log       = "C:\Users\donaldk\work\GCP_service_occupancy_logs\combine_daily_run.log"

# Timestamp at start
Add-Content $Log "`nTask started at $(Get-Date -Format 'dd/MM/yyyy HH:mm:ss')`n"

# Run Python and log all output (stdout + stderr)
& py $Script *>> $Log 2>&1

# Timestamp at end
Add-Content $Log "Task ended at $(Get-Date -Format 'dd/MM/yyyy HH:mm:ss') (ExitCode=$LASTEXITCODE)`n"

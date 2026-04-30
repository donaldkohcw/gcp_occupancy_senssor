# Simple PowerShell wrapper to run everything automatically
# Usage: .\run.ps1 --folder 20573

param(
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$Arguments
)

# Get the directory where this script is located
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Look for service account JSON file
$JsonFile = Get-ChildItem -Path $ScriptDir -Filter "*.json" -ErrorAction SilentlyContinue | Select-Object -First 1

if ($JsonFile) {
    Write-Host "✓ Found credentials: $($JsonFile.Name)"
    $env:GOOGLE_APPLICATION_CREDENTIALS = $JsonFile.FullName
    Write-Host "✓ Credentials configured"
} else {
    Write-Host "[ERROR] No service account JSON file found in $ScriptDir" -ForegroundColor Red
    Write-Host "`nTo set up:"
    Write-Host "1. Go to: https://console.cloud.google.com/"
    Write-Host "2. Create a service account and download the JSON key"
    Write-Host "3. Save it in this folder: $ScriptDir"
    Write-Host "4. Run this script again"
    exit 1
}

# Run the Python script
Write-Host "`nRunning combine_daily.py...`n"
python "$ScriptDir\combine_daily.py" @Arguments

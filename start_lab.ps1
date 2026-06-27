# ==================================================================
#  Bangalore City Hospital - Meditech Lab  (PowerShell launcher)
#
#  Usage (from the project folder):
#      .\start_lab.ps1            # full setup + sender UI
#      .\start_lab.ps1 --no-ui    # setup only
#      .\start_lab.ps1 --down     # stop (keep data)
#      .\start_lab.ps1 --wipe     # stop + delete all data
#
#  If PowerShell blocks the script, run this once in the same window:
#      Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
# ==================================================================

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

function Get-Python {
    if (Get-Command py -ErrorAction SilentlyContinue)     { return @("py", "-3") }
    if (Get-Command python -ErrorAction SilentlyContinue) { return @("python") }
    Write-Host ""
    Write-Host "  Python was not found on PATH." -ForegroundColor Red
    Write-Host "  Install Python 3.11+ from https://www.python.org/downloads/"
    Write-Host "  During install, tick 'Add python.exe to PATH'."
    exit 1
}

$py = Get-Python
& $py[0] $py[1..($py.Length-1)] "run_lab.py" $args

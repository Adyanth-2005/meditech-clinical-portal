# run_postgres.ps1 - start the Meditech gateway in PostgreSQL mode.
#
# Usage (from the advanced folder):
#     .\run_postgres.ps1
#     .\run_postgres.ps1 -Port 8070
#
# Points the store at the lab PostgreSQL container on host port 5433
# (the native Windows PostgreSQL sits on 5432), disables demo mode so
# users/audit persist in the database, and launches uvicorn.
#
# Do NOT run "docker compose down -v" on the lab stack - that wipes the schema.

param(
    [int]$Port = 8060,
    [int]$PgPort = 5433,
    [string]$PgPassword = "adminpassword"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

$venv = Join-Path $root ".venv\Scripts\Activate.ps1"
if (Test-Path $venv) {
    . $venv
} else {
    Write-Warning "venv not found at $venv - using system Python"
}

Write-Host "Checking PostgreSQL container on host port $PgPort ..." -ForegroundColor Cyan
$portLine = (docker port postgres 2>$null) -join " "
if ($portLine -notmatch ":$PgPort") {
    Write-Warning "The postgres container does not appear to publish host port $PgPort."
    Write-Warning "Run 'docker port postgres' to check; pass -PgPort to override."
}

$env:MEDITECH_DEMO   = ""
$env:MEDITECH_PG_DSN = "host=127.0.0.1 port=$PgPort dbname=healthcare_db user=admin password=$PgPassword"

Write-Host "Starting gateway (PostgreSQL mode) on http://127.0.0.1:$Port" -ForegroundColor Green

Set-Location (Join-Path $root "api")
python -m uvicorn app:app --host 127.0.0.1 --port $Port

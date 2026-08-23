[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
    ruff check packages/shadow-kernel/src packages/shadow-application/src adapters/test-deterministic/src adapters/store-sqlite/src apps/shadow-server migrations tests
    pytest -q
    $env:SHADOW_DATABASE_URL = "sqlite://"
    alembic upgrade head
    alembic downgrade base
    git diff --check
    Write-Host "OpenShadow release checks passed."
} finally {
    Pop-Location
}

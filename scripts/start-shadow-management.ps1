[CmdletBinding()]
param(
    [int]$Port = 8765,
    [switch]$Build,
    [switch]$OpenBrowser,
    [string]$RuntimeId,
    [switch]$AutoStartRuntime
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$web = Join-Path $root "apps\shadow-web"
$python = (Get-Command python -ErrorAction Stop).Source

if ($Build) {
    if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
        throw "npm is required when -Build is specified."
    }
    Push-Location $web
    try {
        if (-not (Test-Path (Join-Path $web "node_modules"))) { npm install }
        npm run build
    } finally {
        Pop-Location
    }
}

if (-not (Test-Path (Join-Path $web "dist"))) {
    throw "Web UI build is missing. Run this script with -Build first."
}

$env:SHADOW_RUNTIME_PROFILE_PATH = Join-Path $root "config\runtime-profiles.json"
$server = $null
try {
    $server = Start-Process -FilePath $python `
        -ArgumentList @("-m", "uvicorn", "shadow_server.app:app", "--host", "127.0.0.1", "--port", "$Port") `
        -WorkingDirectory $root -PassThru -WindowStyle Hidden
    $baseUrl = "http://127.0.0.1:$Port"
    $ready = $false
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        try {
            $response = Invoke-RestMethod -Uri "$baseUrl/readyz" -Method Get
            if ($response.status -eq "healthy" -and $response.durable) { $ready = $true; break }
        } catch { }
        Start-Sleep -Milliseconds 250
    }
    if (-not $ready) { throw "Shadow did not become ready within 15 seconds." }

    if ($RuntimeId) {
        $headers = @{ "Idempotency-Key" = "startup-$RuntimeId-$([guid]::NewGuid().ToString())" }
        if ($AutoStartRuntime) {
            Invoke-RestMethod -Uri "$baseUrl/v1/runtime/instances/$([uri]::EscapeDataString($RuntimeId))/start" -Method Post -Headers $headers | Out-Null
        }
        Invoke-RestMethod -Uri "$baseUrl/v1/runtime/instances/$([uri]::EscapeDataString($RuntimeId))/select" -Method Post -Headers $headers | Out-Null
    }

    $managementUrl = "$baseUrl/ui/"
    Write-Host "OpenShadow is ready: $managementUrl"
    Write-Host "Management view: select 'Project management' in the sidebar."
    if ($OpenBrowser) { Start-Process $managementUrl }
    Write-Host "Press Ctrl+C to stop Shadow."
    while (-not $server.HasExited) { Start-Sleep -Seconds 1 }
} finally {
    if ($server -and -not $server.HasExited) {
        Stop-Process -Id $server.Id -Force
    }
}

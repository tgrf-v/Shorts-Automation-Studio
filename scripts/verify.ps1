# Shorts Automation Studio - Skeleton Verification Script (PowerShell)
param(
    [string]$ApiUrl = "http://localhost:8000",
    [string]$WebUrl = "http://localhost:3000"
)

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Shorts Automation Studio - Service Verification" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# 1. Verify API Health
Write-Host "`n[1/3] Checking API Health ($ApiUrl/health)..." -ForegroundColor Yellow
try {
    $apiResp = Invoke-RestMethod -Uri "$ApiUrl/health" -Method Get -TimeoutSec 5
    if ($apiResp.status -eq "ok") {
        Write-Host "API Health: OK (Env: $($apiResp.app_env), Version: $($apiResp.version))" -ForegroundColor Green
    } else {
        Write-Host "API Health returned unexpected status: $($apiResp.status)" -ForegroundColor Red
    }
} catch {
    Write-Host "API is not reachable at $ApiUrl. (Make sure API service is running)" -ForegroundColor DarkYellow
}

# 2. Verify Frontend
Write-Host "`n[2/3] Checking Frontend Web ($WebUrl)..." -ForegroundColor Yellow
try {
    $webResp = Invoke-WebRequest -Uri "$WebUrl" -Method Get -TimeoutSec 5
    if ($webResp.StatusCode -eq 200) {
        Write-Host "Frontend Web: OK (Status 200)" -ForegroundColor Green
    } else {
        Write-Host "Frontend returned status code: $($webResp.StatusCode)" -ForegroundColor Red
    }
} catch {
    Write-Host "Frontend is not reachable at $WebUrl. (Make sure Web service is running)" -ForegroundColor DarkYellow
}

# 3. Verify Docker availability
Write-Host "`n[3/3] Checking Docker CLI..." -ForegroundColor Yellow
if (Get-Command docker -ErrorAction SilentlyContinue) {
    $dockerVer = docker --version
    Write-Host "Docker is available: $dockerVer" -ForegroundColor Green
} else {
    Write-Host "Docker CLI not detected in PATH. Services can be run directly via npm and uvicorn." -ForegroundColor DarkYellow
}

Write-Host "`nVerification complete." -ForegroundColor Cyan

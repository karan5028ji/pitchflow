<#
.SYNOPSIS
    PitchFlow - 1-Click Launch & Setup Script
.DESCRIPTION
    Automates environment verification, dependency installation, and starts the PitchFlow Web Studio.
    Usage:
        irm https://raw.githubusercontent.com/karan5028ji/pitchflow/main/run.ps1 | iex
#>

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "             🎵 Welcome to PitchFlow Studio ✉️              " -ForegroundColor Cyan
Write-Host "   Autonomous Music PR & Curator Outreach Engine v1.0.0     " -ForegroundColor DarkGray
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Determine target directory
$TargetDir = "$env:LOCALAPPDATA\PitchFlow"
if (Test-Path "main.py") {
    $TargetDir = Get-Location
    Write-Host "[*] Running directly from local workspace: $TargetDir" -ForegroundColor Yellow
} else {
    Write-Host "[*] Setting up PitchFlow in $TargetDir..." -ForegroundColor Yellow
    if (!(Test-Path $TargetDir)) {
        New-Item -ItemType Directory -Path $TargetDir | Out-Null
    }
    Set-Location $TargetDir
    if (!(Test-Path ".git")) {
        Write-Host "[*] Cloning latest PitchFlow repository..." -ForegroundColor Yellow
        git clone https://github.com/karan5028ji/pitchflow.git .
    } else {
        Write-Host "[*] Pulling latest updates..." -ForegroundColor Yellow
        git pull origin main
    }
}

# 1. Check Python installation
Write-Host "[*] Verifying Python installation..." -ForegroundColor Cyan
$PythonCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonCmd = "python"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $PythonCmd = "py -3"
}

if (-not $PythonCmd) {
    Write-Host "[!] Python 3 not found on your system!" -ForegroundColor Red
    Write-Host "[*] Installing Python 3 via winget..." -ForegroundColor Yellow
    winget install Python.Python.3.11 --silent --accept-package-agreements --accept-source-agreements
    $PythonCmd = "python"
}

# 2. Setup Virtual Environment
if (!(Test-Path "venv")) {
    Write-Host "[*] Creating virtual environment (.venv)..." -ForegroundColor Cyan
    & $PythonCmd -m venv venv
}

# 3. Activate Virtual Environment
Write-Host "[*] Activating virtual environment..." -ForegroundColor Cyan
$VenvPython = ".\venv\Scripts\python.exe"
if (!(Test-Path $VenvPython)) {
    $VenvPython = $PythonCmd
}

# 4. Install / Verify Dependencies
Write-Host "[*] Checking & installing dependencies..." -ForegroundColor Cyan
& $VenvPython -m pip install --upgrade pip --quiet
& $VenvPython -m pip install -r requirements.txt --quiet

# 5. Launch PitchFlow Web Studio
Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  🚀 Launching PitchFlow Studio on http://localhost:8000    " -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""

& $VenvPython main.py gui

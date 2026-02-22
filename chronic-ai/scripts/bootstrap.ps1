Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step([string]$Message) {
    Write-Host "[bootstrap] $Message"
}

function Invoke-StepCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Description,
        [Parameter(Mandatory = $true)]
        [scriptblock]$Command
    )

    Write-Step $Description
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "[bootstrap] Failed: $Description (exit code $LASTEXITCODE)"
    }
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$venvDir = Join-Path $repoRoot ".venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"
$apiEnvFile = Join-Path $repoRoot "api\.env"
$apiEnvExampleFile = Join-Path $repoRoot "api\.env.example"
$frontendEnvFile = Join-Path $repoRoot "frontend\.env.local"

Write-Step "Repository root: $repoRoot"

Write-Step "Checking runtime versions"
python --version
node --version
npm --version

if (-not (Test-Path $venvPython)) {
    Invoke-StepCommand "Creating Python virtual environment at $venvDir" { python -m venv $venvDir }
}

Invoke-StepCommand "Upgrading pip" { & $venvPython -m pip install --upgrade pip }

Invoke-StepCommand "Installing API dependencies" {
    & $venvPython -m pip install -r (Join-Path $repoRoot "api\requirements.txt")
}

Invoke-StepCommand "Installing ECG classifier dependencies" {
    & $venvPython -m pip install -r (Join-Path $repoRoot "ecg_classifier\requirements.txt")
}

Invoke-StepCommand "Installing frontend dependencies via lockfile" {
    Push-Location (Join-Path $repoRoot "frontend")
    try {
        npm ci
    } finally {
        Pop-Location
    }
}

if (-not (Test-Path $apiEnvFile)) {
    if (Test-Path $apiEnvExampleFile) {
        Write-Step "Creating api/.env from api/.env.example"
        Copy-Item $apiEnvExampleFile $apiEnvFile
    } else {
        throw "[bootstrap] Missing env template: $apiEnvExampleFile"
    }
}

if (-not (Test-Path $frontendEnvFile)) {
    Write-Step "Creating frontend/.env.local with default API URL"
    Set-Content -Path $frontendEnvFile -Value "NEXT_PUBLIC_API_URL=http://localhost:8000"
}

Write-Step "Bootstrap complete"
Write-Step "Next: fill api/.env secrets and start services"

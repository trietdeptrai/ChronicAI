Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step([string]$Message) {
    Write-Host "[bootstrap] $Message"
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$venvDir = Join-Path $repoRoot ".venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"
$venvPip = Join-Path $venvDir "Scripts\pip.exe"

Write-Step "Repository root: $repoRoot"

Write-Step "Checking runtime versions"
python --version
node --version
npm --version

if (-not (Test-Path $venvPython)) {
    Write-Step "Creating Python virtual environment at $venvDir"
    python -m venv $venvDir
}

Write-Step "Upgrading pip"
& $venvPython -m pip install --upgrade pip

Write-Step "Installing API dependencies"
& $venvPip install -r (Join-Path $repoRoot "api\requirements.txt")

Write-Step "Installing ECG classifier dependencies"
& $venvPip install -r (Join-Path $repoRoot "ecg_classifier\requirements.txt")

Write-Step "Installing frontend dependencies via lockfile"
Push-Location (Join-Path $repoRoot "frontend")
try {
    npm ci
} finally {
    Pop-Location
}

Write-Step "Bootstrap complete"
Write-Step "Next: copy env templates and start services"

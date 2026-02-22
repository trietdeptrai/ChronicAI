#!/usr/bin/env bash
set -euo pipefail

step() {
  printf '[bootstrap] %s\n' "$1"
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
VENV_DIR="${REPO_ROOT}/.venv"
VENV_PYTHON="${VENV_DIR}/bin/python"
VENV_PIP="${VENV_DIR}/bin/pip"

step "Repository root: ${REPO_ROOT}"

step "Checking runtime versions"
python3 --version
node --version
npm --version

if [[ ! -x "${VENV_PYTHON}" ]]; then
  step "Creating Python virtual environment at ${VENV_DIR}"
  python3 -m venv "${VENV_DIR}"
fi

step "Upgrading pip"
"${VENV_PYTHON}" -m pip install --upgrade pip

step "Installing API dependencies"
"${VENV_PIP}" install -r "${REPO_ROOT}/api/requirements.txt"

step "Installing ECG classifier dependencies"
"${VENV_PIP}" install -r "${REPO_ROOT}/ecg_classifier/requirements.txt"

step "Installing frontend dependencies via lockfile"
(
  cd "${REPO_ROOT}/frontend"
  npm ci
)

step "Bootstrap complete"
step "Next: copy env templates and start services"

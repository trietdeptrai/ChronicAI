#!/usr/bin/env bash
set -euo pipefail

step() {
  printf '[bootstrap] %s\n' "$1"
}

run_step() {
  step "$1"
  shift
  "$@"
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
VENV_DIR="${REPO_ROOT}/.venv"
VENV_PYTHON="${VENV_DIR}/bin/python"
API_ENV_FILE="${REPO_ROOT}/api/.env"
API_ENV_EXAMPLE_FILE="${REPO_ROOT}/api/.env.example"
FRONTEND_ENV_FILE="${REPO_ROOT}/frontend/.env.local"

step "Repository root: ${REPO_ROOT}"

step "Checking runtime versions"
python3 --version
node --version
npm --version

if [[ ! -x "${VENV_PYTHON}" ]]; then
  run_step "Creating Python virtual environment at ${VENV_DIR}" python3 -m venv "${VENV_DIR}"
fi

run_step "Upgrading pip" "${VENV_PYTHON}" -m pip install --upgrade pip

run_step "Installing API dependencies" "${VENV_PYTHON}" -m pip install -r "${REPO_ROOT}/api/requirements.txt"

run_step "Installing ECG classifier dependencies" "${VENV_PYTHON}" -m pip install -r "${REPO_ROOT}/ecg_classifier/requirements.txt"

step "Installing frontend dependencies via lockfile"
(
  cd "${REPO_ROOT}/frontend"
  npm ci
)

if [[ ! -f "${API_ENV_FILE}" ]]; then
  if [[ -f "${API_ENV_EXAMPLE_FILE}" ]]; then
    step "Creating api/.env from api/.env.example"
    cp "${API_ENV_EXAMPLE_FILE}" "${API_ENV_FILE}"
  else
    printf '[bootstrap] Missing env template: %s\n' "${API_ENV_EXAMPLE_FILE}" >&2
    exit 1
  fi
fi

if [[ ! -f "${FRONTEND_ENV_FILE}" ]]; then
  step "Creating frontend/.env.local with default API URL"
  printf 'NEXT_PUBLIC_API_URL=http://localhost:8000\n' > "${FRONTEND_ENV_FILE}"
fi

step "Bootstrap complete"
step "Next: fill api/.env secrets and start services"

#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

VENV="$ROOT/.venv"
if [[ ! -d "$VENV" ]]; then
  echo "Creating venv at $VENV"
  python3 -m venv "$VENV"
fi

"$VENV/bin/pip" install -q -r requirements.txt

load_env_file() {
  local f="$1"
  echo "Loading environment from $f"
  set -a
  # shellcheck disable=SC1090
  source "$f"
  set +a
}

if [[ -n "${PYWE_ENV_FILE:-}" && -f "${PYWE_ENV_FILE}" ]]; then
  load_env_file "${PYWE_ENV_FILE}"
elif [[ -f "$ROOT/dev.env" ]]; then
  load_env_file "$ROOT/dev.env"
elif [[ -f "$ROOT/.env" ]]; then
  load_env_file "$ROOT/.env"
fi

if [[ -n "${DJANGO_SECRET_KEY:-}" && -z "${SECRET_KEY:-}" ]]; then
  export SECRET_KEY="$DJANGO_SECRET_KEY"
fi

# Env files may set DJANGO_SETTINGS_MODULE for another project; force this tree.
export DJANGO_SETTINGS_MODULE=pywe_cms_backend.settings

"$VENV/bin/python" manage.py migrate --noinput
exec "$VENV/bin/python" manage.py runserver "$@"

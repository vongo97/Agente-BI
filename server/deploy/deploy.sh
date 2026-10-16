#!/usr/bin/env bash
# =============================================================================
# Deploy de actualización en el VPS (correr en el servidor como vektra o admin)
# Uso:  bash deploy.sh
# Hace: git pull -> sync de dependencias -> reinicio del servicio -> health check
# =============================================================================
set -euo pipefail

APP_DIR="/opt/vektra/repo"
SERVICE="vektra"

cd "${APP_DIR}"

echo "==> [1/4] Traer últimos cambios"
STASHED=0
if ! git diff --quiet || ! git diff --cached --quiet; then
  git stash && STASHED=1
fi
git pull --ff-only origin main
if [ "${STASHED}" -eq 1 ]; then
  echo "    (Había cambios locales; se guardaron en stash: 'git stash pop' si los necesitas)"
fi

echo "==> [2/4] Sincronizar dependencias"
if [ ! -d "${APP_DIR}/server/.venv" ]; then
  python3 -m venv "${APP_DIR}/server/.venv"
fi
"${APP_DIR}/server/.venv/bin/pip" install --quiet --upgrade pip
"${APP_DIR}/server/.venv/bin/pip" install --quiet -r "${APP_DIR}/server/requirements.txt"

echo "==> [3/4] Reiniciar servicio"
sudo systemctl restart "${SERVICE}"
sleep 4

echo "==> [4/4] Health check local"
if curl -sf http://127.0.0.1:8000/health >/dev/null; then
  echo "✅ Deploy OK — backend vivo."
  curl -s http://127.0.0.1:8000/health
else
  echo "❌ El backend no responde tras el reinicio. Revisa:"
  echo "   sudo journalctl -u ${SERVICE} -n 50 --no-pager"
  exit 1
fi

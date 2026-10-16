#!/usr/bin/env bash
# =============================================================================
# Bootstrap ONE-TIME del VPS (Ubuntu 24.04) para Vektra-BI backend
# Uso:  sudo bash setup_server.sh
# Idempotente: se puede re-ejecutar sin romper nada.
# =============================================================================
set -euo pipefail

APP_USER="vektra"
APP_DIR="/opt/vektra"

echo "==> [1/6] Paquetes base"
apt-get update -y
apt-get install -y python3 python3-venv python3-pip git curl ufw

echo "==> [2/6] Caddy (reverse proxy con HTTPS automático)"
if ! command -v caddy >/dev/null 2>&1; then
  apt-get install -y debian-keyring debian-archive-keyring apt-transport-https curl
  install -d /usr/share/keyrings
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list >/dev/null
  apt-get update -y
  apt-get install -y caddy
fi

echo "==> [3/6] Usuario de servicio '${APP_USER}' (sin password, SSH por llave)"
if ! id "${APP_USER}" >/dev/null 2>&1; then
  adduser --disabled-password --gecos "Vektra BI service" "${APP_USER}"
fi
usermod -aG www-data "${APP_USER}" || true

echo "==> [4/6] Firewall ufw (22/80/443)"
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
yes | ufw enable || true
ufw status

echo "==> [5/6] Estructura de directorios"
mkdir -p "${APP_DIR}"
# El código lo clona el admin tras autenticarse con git; ajustamos dueños al final.

echo "==> [6/6] SSH: deshabilitar login por password (solo llaves)"
SSHD_CONF="/etc/ssh/sshd_config.d/99-vektra-hardening.conf"
cat > "${SSHD_CONF}" <<'EOF'
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin prohibit-password
EOF
systemctl reload ssh 2>/dev/null || systemctl reload sshd || true

echo ""
echo "✅ Bootstrap completo. Siguientes pasos (como tu usuario admin, NO como root):"
echo "   1) sudo mkdir -p ${APP_DIR} && sudo chown ${APP_USER}:${APP_USER} ${APP_DIR}"
echo "   2) sudo -u ${APP_USER} git clone https://github.com/vongo97/Agente-BI ${APP_DIR}/repo"
echo "   3) Copiar env.template -> ${APP_DIR}/repo/server/.env y rellenar valores reales"
echo "   4) sudo cp ${APP_DIR}/repo/server/deploy/vektra.service /etc/systemd/system/"
echo "   5) sudo systemctl daemon-reload && sudo systemctl enable --now vektra"
echo "   6) Copiar Caddyfile y recargar caddy (ver README.md)"

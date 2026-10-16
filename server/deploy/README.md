# Deploy del backend en VPS (Oracle Always Free / cualquier Ubuntu 24.04)

Arquitectura: `Caddy (443, HTTPS auto) → uvicorn (127.0.0.1:8000, systemd)`.

> Decisión: **systemd + venv, sin Docker** para minimizar piezas en una VM
> pequeña de un solo servicio. Docker multi-stage se puede añadir después si
> el proyecto crece (ver skill deployment-and-ci-cd-pipelines).

## Flujo completo (una sola vez)

### 0. Prerrequisitos
- VM ARM (A1) o x86 con **Ubuntu 24.04**, IP pública, y acceso SSH con tu llave.
- Un dominio (propio o gratis en DuckDNS) apuntando con registro **A** a la IP.

### 1. ⚠️ OCI: abrir 80/443 en el firewall de NUBE (el paso que todos olvidan)
Oracle tiene firewall **por fuera** del sistema operativo:
`Console → Networking → Virtual Cloud Networks → tu VCN → Security Lists → Default Security List → Add Ingress Rules`:

| Source CIDR | Protocol | Dest Port |
|---|---|---|
| 0.0.0.0/0 | TCP | 80 |
| 0.0.0.0/0 | TCP | 443 |

(El puerto 22 ya viene abierto por la regla default de SSH.)

### 2. SSH al servidor y bootstrap
```bash
ssh ubuntu@TU_IP
curl -fsSL https://raw.githubusercontent.com/vongo97/Agente-BI/main/server/deploy/setup_server.sh -o /tmp/setup.sh
sudo bash /tmp/setup.sh
```

### 3. Clonar el repo y configurar el entorno
```bash
sudo mkdir -p /opt/vektra && sudo chown vektra:vektra /opt/vektra
sudo -u vektra git clone https://github.com/vongo97/Agente-BI /opt/vektra/repo
sudo -u vektra cp /opt/vektra/repo/server/deploy/env.template /opt/vektra/repo/server/.env
sudo -u vektra nano /opt/vektra/repo/server/.env   # rellenar con los VALORES REALES de Render
```
⚠️ `ENCRYPTION_KEY` debe ser **idéntica** a la de Render (si cambia, las claves
API cifradas en la DB dejan de ser legibles). `AUTH_SECRET` idéntico al de Vercel.

### 4. Servicio systemd + venv
```bash
sudo -u vektra python3 -m venv /opt/vektra/repo/server/.venv
sudo cp /opt/vektra/repo/server/deploy/vektra.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now vektra
sudo journalctl -u vektra -n 30 --no-pager   # debe terminar en "Application startup complete"
```

### 5. Caddy + dominio
```bash
sudo cp /opt/vektra/repo/server/deploy/Caddyfile /etc/caddy/Caddyfile
sudo sed -i 's/TU_DOMINIO/api.tudominio.com/' /etc/caddy/Caddyfile
sudo systemctl reload caddy
```
Con el registro DNS apuntando, Caddy emite el certificado TLS solo.

### 6. Verificación
```bash
curl https://TU_DOMINIO/health
# Esperado: database.persistent=true y storage.connected=true
```

### 7. Conmutar el tráfico (sin downtime)
- Render sigue vivo como respaldo hasta verificar todo.
- Vercel → `NEXT_PUBLIC_API_URL=https://TU_DOMINIO` → redeploy.
- `ALLOWED_ORIGINS` del backend ya incluye el dominio de Vercel.
- Probar: login Google → Seguridad y Llaves → validar clave → subir CSV → análisis.

### 8. Desplegar cambios futuros
```bash
ssh ubuntu@TU_IP
sudo -u vektra bash /opt/vektra/repo/server/deploy/deploy.sh
```

## Solución de problemas
| Síntoma | Causa probable | Fix |
|---|---|---|
| Timeout desde fuera pero curl local funciona | Ingress rules de OCI | Paso 1 |
| Caddy no emite certificado | DNS no propagado o puerto 80 cerrado | Esperar DNS / revisar paso 1 |
| `401 Se requiere token` | `ENVIRONMENT` ≠ production o `AUTH_SECRET` distinto al de Vercel | Revisar .env |
| Claves API ilegibles | `ENCRYPTION_KEY` distinta a la de Render | Poner la original |
| Service no arranca | Permisos o venv ausente | `journalctl -u vektra -n 50` |

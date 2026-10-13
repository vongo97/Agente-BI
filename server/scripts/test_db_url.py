"""Diagnóstico de DATABASE_URL para Vektra-BI.

Uso:
    python server/scripts/test_db_url.py "postgresql://user:pass@host:5432/postgres?sslmode=require"
    # o con variable de entorno:
    set DATABASE_URL=postgresql://...   (Windows)
    python server/scripts/test_db_url.py

Hace las mismas comprobaciones que Render hará al arrancar:
  1. Parseo del URL y mascarado de la contraseña.
  2. DNS del host (detecta hosts solo-IPv6 que Render free no resuelve).
  3. Conexión TCP al puerto (host:5432).
  4. Conexión SQLAlchemy real + SELECT version().
  5. tablas detectadas (sin tocar datos).

Salida siempre sin exponer la contraseña.
"""

from __future__ import annotations

import os
import socket
import sys
from urllib.parse import urlsplit

# Consolas Windows en cp1252: fuerza UTF-8 para que acentos y marcas no rompan.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def mask(url: str) -> str:
    """Oculta la contraseña: postgresql://user:****@host:port/db"""
    try:
        parts = urlsplit(url)
        auth = parts.username or ""
        if parts.password:
            auth += ":****"
        host = parts.hostname or ""
        port = parts.port or ""
        return f"{parts.scheme}://{auth}@{host}:{port}{parts.path}"
    except Exception:
        return "<URL mal formada>"


def paso(n: int, texto: str) -> None:
    print(f"\n[PASO {n}] {texto}")


def ok(texto: str) -> None:
    print(f"  [OK] {texto}")


def warn(texto: str) -> None:
    print(f"  [NOTA] {texto}")


def fail(texto: str) -> None:
    print(f"  [FALLO] {texto}")


def main() -> int:
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = os.getenv("DATABASE_URL", "")

    if not url:
        fail("No has pasado ninguna URL.")
        print('  Uso: python server/scripts/test_db_url.py "postgresql://..."')
        print("  O establece la variable de entorno DATABASE_URL y ejecuta sin argumentos.")
        return 2

    print(f"Probando: {mask(url)}")

    # ---- PASO 1: parseo ----
    paso(1, "Parseo del URL")
    try:
        parts = urlsplit(url)
        if parts.scheme not in ("postgresql", "postgres"):
            warn(f"El esquema es '{parts.scheme}'; SQLAlchemy acepta postgresql:// (postgres:// también sirve).")
        host = parts.hostname
        port = parts.port or 5432
        dbname = (parts.path or "").lstrip("/") or "postgres"
        if not host:
            fail("El URL no tiene host.")
            return 2
        ok(f"Host: {host}:{port} · DB: {dbname} · Usuario: {parts.username}")
        if "sslmode" not in url:
            warn("No se ve 'sslmode=require' en el URL — sin él Supabase puede rechazar la conexión desde Render.")
    except Exception as e:
        fail(f"URL mal formada: {e}")
        return 2

    # ---- PASO 2: DNS ----
    paso(2, "Resolución DNS del host")
    try:
        infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
        ips = sorted({i[4][0] for i in infos})
        v4 = [ip for ip in ips if ":" not in ip]
        v6 = [ip for ip in ips if ":" in ip]
        ok(f"DNS OK -> {len(ips)} IPs (IPv4: {len(v4)}, IPv6: {len(v6)})")
        if not v4:
            warn("Solo hay IPv6. El plan free de Render no lo resuelve — usa el pooler de sesión.")
    except socket.gaierror as e:
        fail(f"No se pudo resolver el host: {e}")
        warn("¿El hostname está bien escrito? Para Supabase usa aws-1-sa-east-1.pooler.supabase.com (no db.<ref>.supabase.co).")
        return 1

    # ---- PASO 3: TCP ----
    paso(3, "Conexión TCP al puerto")
    try:
        with socket.create_connection((host, port), timeout=10):
            pass
        ok("TCP OK — el puerto está abierto y alcanzable.")
    except OSError as e:
        fail(f"No se pudo conectar a {host}:{port}: {e}")
        warn("¿El pooler está activo? ¿Render/PC tiene salida al puerto 5432?")
        return 1

    # ---- PASO 4: conexión SQLAlchemy real ----
    paso(4, "Conexión SQLAlchemy")
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(url, connect_args={"connect_timeout": 10}, pool_pre_ping=True)
        with engine.connect() as conn:
            version = conn.execute(text("SELECT version()")).scalar()
            ok(f"Conectado -> {version.split(',')[0]}")
        engine.dispose()
    except Exception as e:
        msg = str(e)
        fail(f"Conexión rechazada: {type(e).__name__}")
        print(f"     (detalle: {msg.splitlines()[0][:140]})")
        if "Tenant or user not found" in msg:
            print("  -> El PROJECT_REF del usuario no existe o no corresponde al pooler.")
            print("     Verifica el ref en: Supabase Dashboard - Settings - General - Reference ID.")
        elif "password authentication failed" in msg:
            print("  -> Contraseña equivocada. Settings - Database - Reset database password.")
        elif "no pg_hba.conf" in msg or "SSL" in msg.lower():
            print("  -> Falta sslmode=require al final del URL.")
        elif "timeout" in msg.lower():
            print("  -> El pooler no está respondiendo; revisa Pooler Mode y región.")
        return 1

    # ---- PASO 5: tablas ----
    paso(5, "Verificación de esquema")
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(url, connect_args={"connect_timeout": 10})
        with engine.connect() as conn:
            tables = conn.execute(
                text("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY 1")
            ).scalars().all()
        engine.dispose()
        if tables:
            ok(f"{len(tables)} tablas: {', '.join(tables)}")
            if "data_sources" in tables and "user_configs" in tables:
                ok("Esquema de Vektra presente — persistencia real lista.")
            else:
                warn("Faltan tablas de Vektra (¿la migración/creación aún no corrió en este proyecto?).")
        else:
            warn("La base está vacía. En el primer arranque deberían crearse las tablas (init_db).")
    except Exception as e:
        fail(f"La conexión funciona, pero no pude listar tablas: {e}")
        return 1

    print("\n=== RESUMEN: la URL PASA todas las comprobaciones. Cópiala tal cual en Render ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())

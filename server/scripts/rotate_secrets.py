"""
rotate_secrets.py — Rotación segura de AUTH_SECRET y ENCRYPTION_KEY.

Qué hace:
1. Lee las claves actuales desde server/.env (o variables de entorno).
2. Genera nuevas: ENCRYPTION_KEY (Fernet) y AUTH_SECRET (aleatoria fuerte).
3. MIGRA todos los datos cifrados con la clave vieja a la nueva:
   - user_configs: gemini_key, mistral_key, gamma_key, groq_key (+ columna ok)
   - data_sources.url cuando empieza por el prefijo Fernet 'gAAAA' (URL SQL cifrada)
   - Archivos cifrados en data_sources/ y sessions_cache/ (prefijo 'gAAA')
4. Escribe el nuevo .env (con backup en .env.bak-<timestamp>).

USO (desde la raíz del proyecto, con el venv del servidor):
    server\\.venv-codex\\Scripts\\python.exe -m server.scripts.rotate_secrets
    (o) cd server && .\\.venv-codex\\Scripts\\python.exe scripts\\rotate_secrets.py

⚠️ Tras rotar AUTH_SECRET todas las sesiones JWT existentes quedan invalidadas
   (los usuarios deberán volver a iniciar sesión). La MISMA AUTH_SECRET debe
   configurarse en el frontend (client/.env.local o Vercel) y en el backend.
"""
import os
import sys
import secrets
import shutil
from datetime import datetime

# Asegurar imports del backend
SERVER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SERVER_DIR)
os.environ.setdefault(
    "DATABASE_URL",
    f"sqlite:///{os.path.abspath(os.path.join(SERVER_DIR, 'test_bi.db'))}",
)

from cryptography.fernet import Fernet

ENV_PATH = os.path.join(SERVER_DIR, ".env")


def read_env(path):
    values = {}
    lines = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            lines.append(line.rstrip("\n"))
            s = line.strip()
            if s and not s.startswith("#") and "=" in s:
                k, v = s.split("=", 1)
                values[k.strip()] = v.strip()
    return lines, values


def write_env(path, lines, updates):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        written = set()
        for line in lines:
            s = line.strip()
            if s and not s.startswith("#") and "=" in s:
                k = s.split("=", 1)[0].strip()
                if k in updates:
                    f.write(f"{k}={updates[k]}\n")
                    written.add(k)
                    continue
            f.write(line + "\n")
        for k, v in updates.items():
            if k not in written:
                f.write(f"{k}={v}\n")


def reencrypt_text(old_c, new_c, value):
    """Si el valor parece Fernet, lo migra. Si no, lo devuelve intacto."""
    if not value or not isinstance(value, str):
        return value, False
    if not value.startswith("gAAAA"):
        return value, False
    try:
        plain = old_c.decrypt(value.encode())
        return new_c.encrypt(plain).decode(), True
    except Exception:
        return value, False


def reencrypt_file(old_c, new_c, path):
    """Migra un archivo Fernet sólo si empieza por el token 'gAAA'. Retorna True si migró."""
    try:
        with open(path, "rb") as f:
            data = f.read()
        if not data.strip().startswith(b"gAAA"):
            return False
        plain = old_c.decrypt(data)
        with open(path, "wb") as f:
            f.write(new_c.encrypt(plain))
        return True
    except Exception as e:
        print(f"   [SKIP] {os.path.basename(path)}: no se pudo migrar ({type(e).__name__})")
        return False


def main():
    if not os.path.exists(ENV_PATH):
        print(f"[ERROR] No existe {ENV_PATH}")
        sys.exit(1)

    lines, env = read_env(ENV_PATH)
    old_key = env.get("ENCRYPTION_KEY") or os.getenv("ENCRYPTION_KEY")
    old_auth = env.get("AUTH_SECRET") or os.getenv("AUTH_SECRET")
    if not old_key:
        print("[ERROR] ENCRYPTION_KEY no definida en .env ni en el entorno.")
        sys.exit(1)

    new_encryption_key = Fernet.generate_key().decode()
    new_auth_secret = secrets.token_urlsafe(48)

    old_fernet = Fernet(old_key.encode())
    new_fernet = Fernet(new_encryption_key.encode())

    print("== Rotación de secretos Vektra BI ==")
    print("- Nueva ENCRYPTION_KEY generada.")
    print("- Nueva AUTH_SECRET generada (64+ bits de entropía).\n")

    # 1) Base de datos (SQL crudo para no depender del estado del modelo ORM)
    print("== Migrando DB ==")
    from src.database import engine
    from sqlalchemy import text
    migrated_rows = 0
    with engine.begin() as conn:
        key_cols = ("gemini_key", "mistral_key", "gamma_key", "groq_key")
        rows = conn.execute(text("SELECT user_id, gemini_key, mistral_key, gamma_key, groq_key FROM user_configs")).all()
        for r in rows:
            updates = {}
            for col in key_cols:
                new_val, did = reencrypt_text(old_fernet, new_fernet, r._mapping[col])
                if did:
                    updates[col] = new_val
            if updates:
                set_clause = ", ".join(f"{c} = :{c}" for c in updates)
                params = {**updates, "uid": r._mapping["user_id"]}
                conn.execute(text(f"UPDATE user_configs SET {set_clause} WHERE user_id = :uid"), params)
                migrated_rows += 1
        rows = conn.execute(text("SELECT id, type, url FROM data_sources WHERE type = 'sql'")).all()
        for r in rows:
            new_val, did = reencrypt_text(old_fernet, new_fernet, r._mapping["url"])
            if did:
                conn.execute(text("UPDATE data_sources SET url = :u WHERE id = :i"), {"u": new_val, "i": r._mapping["id"]})
                migrated_rows += 1
    print(f"   ✔ {migrated_rows} filas migradas en la DB ({os.environ.get('DATABASE_URL','')})")

    # 2) Archivos cifrados en disco (server/ y raíz del proyecto)
    print("== Migrando archivos cifrados ==")
    project_root = os.path.abspath(os.path.join(SERVER_DIR, ".."))
    targets = []
    for base in (SERVER_DIR, project_root):
        for sub in ("data_sources", "sessions_cache"):
            d = os.path.join(base, sub)
            if os.path.isdir(d):
                for name in os.listdir(d):
                    p = os.path.join(d, name)
                    if os.path.isfile(p) and not name.endswith((".tmp", ".encrypting")):
                        targets.append(p)
    n_files = 0
    for p in targets:
        if reencrypt_file(old_fernet, new_fernet, p):
            n_files += 1
    print(f"   ✔ {n_files} archivos migrados a la nueva clave")

    # 3) Escribir .env nuevo con backup
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = f"{ENV_PATH}.bak-{stamp}"
    shutil.copy2(ENV_PATH, backup)
    write_env(ENV_PATH, lines, {
        "ENCRYPTION_KEY": new_encryption_key,
        "AUTH_SECRET": new_auth_secret,
    })
    print(f"   ✔ .env actualizado (backup: {os.path.basename(backup)})")

    # 4) Sincronizar AUTH_SECRET con el frontend local (si existe)
    client_env = os.path.join(project_root, "client", ".env.local")
    if os.path.exists(client_env):
        c_lines, c_values = read_env(client_env)
        if "AUTH_SECRET" in c_values or "NEXTAUTH_SECRET" in c_values:
            shutil.copy2(client_env, f"{client_env}.bak-{stamp}")
            write_env(client_env, c_lines, {"AUTH_SECRET": new_auth_secret})
            print("   ✔ client/.env.local actualizado con la misma AUTH_SECRET")
            print("     (Vercel: actualiza AUTH_SECRET manualmente en Variables de entorno)")

    print("\n======= RESULTADO =======")
    print("ENCRYPTION_KEY: rotada ✔ (nunca mostrada en pantalla)")
    print("Nueva AUTH_SECRET (cópiala AHORA, no se volverá a mostrar):")
    print("-" * 60)
    print(new_auth_secret)
    print("-" * 60)
    print("\n⚠️ PASOS OBLIGATORIOS TRAS ESTA ROTACIÓN:")
    print("1. El frontend (client/.env.local y en Vercel) debe usar ESTA misma AUTH_SECRET,")
    print("   si no, el backend rechazará todos los tokens activos (401).")
    print("2. Todas las sesiones activas quedan invalidadas (re-login).")
    print("3. Borra los backups .env.bak-* cuando hayas validado que todo funciona.")


if __name__ == "__main__":
    main()

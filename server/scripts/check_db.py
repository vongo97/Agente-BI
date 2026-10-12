"""
Comprobación de conectividad con la base de datos.

Útil antes de pegar DATABASE_URL en Render: verifica desde tu máquina que el host,
el puerto, el usuario y la contraseña son correctos, sin ensuciar el repo ni el
historial de la consola con secretos.

Uso:
    python server/scripts/check_db.py
    python server/scripts/check_db.py --url "postgresql://usuario:pass@host:5432/db?sslmode=require"

No imprime la contraseña en ningún momento.
"""
import argparse
import getpass
import os
import sys

DEFAULT_HOST = "aws-1-sa-east-1.pooler.supabase.com"   # Session pooler, región sa-east-1
DEFAULT_USER = "postgres.tvypzabjhtngepggfqnb"
DEFAULT_DB = "postgres"
DEFAULT_PORT = 5432

METHODS = {
    "session": ("Session pooler", DEFAULT_PORT, "aws-1-sa-east-1.pooler.supabase.com"),
    "transaction": ("Transaction pooler", 6543, "aws-1-sa-east-1.pooler.supabase.com"),
    "direct": ("Direct connection (IPv6, NO usar en Render free)", 5432, "db.tvypzabjhtngepggfqnb.supabase.co"),
}


def build_url(host: str, port: int, user: str, db: str, password: str) -> str:
    # La contraseña va URL-encoded: si contiene @ : / ? # rompe el parseo de la URI.
    from urllib.parse import quote
    return f"postgresql://{quote(user, safe='')}:{quote(password, safe='')}@{host}:{port}/{db}?sslmode=require"


def masked(url: str) -> str:
    if "@" not in url or ":" not in url.split("@")[0]:
        return url
    scheme, rest = url.split("://", 1)
    creds, hostpart = rest.split("@", 1)
    user = creds.split(":")[0]
    return f"{scheme}://{user}:***@{hostpart}"


def main() -> int:
    ap = argparse.ArgumentParser(description="Comprueba la conexión a la base de datos")
    ap.add_argument("--url", help="Usar esta URL directamente (sin password se pide)")
    ap.add_argument("--host", default=os.getenv("PGHOST", DEFAULT_HOST))
    ap.add_argument("--port", type=int, default=int(os.getenv("PGPORT", DEFAULT_PORT)))
    ap.add_argument("--user", default=os.getenv("PGUSER", DEFAULT_USER))
    ap.add_argument("--db", default=os.getenv("PGDATABASE", DEFAULT_DB))
    ap.add_argument("--method", choices=list(METHODS), default=os.getenv("PGMETHOD", "session"))
    args = ap.parse_args()

    if args.url:
        url = args.url
        if "://" in url and "@" in url:
            scheme, rest = url.split("://", 1)
            creds, hostpart = rest.split("@", 1)
            if ":" in creds and not creds.split(":", 1)[1]:
                user = creds.split(":", 1)[0]
                url = url.replace(f"{creds}", f"{user}:{quote(getpass.getpass('Contraseña: '), safe='')}", 1)
    else:
        label, default_port, default_host = METHODS[args.method]
        print(f"Método: {label}")
        host = input(f"Host [{default_host}]: ").strip() or default_host
        port = int(input(f"Puerto [{default_port}]: ").strip() or default_port)
        user = input(f"Usuario [{args.user}]: ").strip() or args.user
        db = input(f"Base de datos [{args.db}]: ").strip() or args.db
        password = getpass.getpass("Contraseña (no se muestra): ")
        url = build_url(host, port, user, db, password)

    print(f"Probando: {masked(url)}")
    try:
        import sqlalchemy as sa
    except ImportError:
        print("Falta SQLAlchemy: pip install sqlalchemy psycopg2-binary")
        return 2

    try:
        engine = sa.create_engine(url, connect_args={"connect_timeout": 10})
        with engine.connect() as conn:
            version = conn.execute(sa.text("select version()")).scalar()
        engine.dispose()
        print(f"CONEXION OK -> {str(version).split(',')[0]}")
        return 0
    except Exception as exc:
        print(f"FALLO: {type(exc).__name__}")
        msg = str(exc)
        if "password authentication failed" in msg or "fe_sendauth: no password" in msg:
            print("  -> Usuario o contrasena incorrectos (o caracteres especiales sin codificar).")
        elif "could not translate host name" in msg or "Name or service not known" in msg:
            print("  -> El host no existe. Comprueba si es el pooler o la conexion directa.")
        elif "timeout" in msg.lower() or "timed out" in msg.lower():
            print("  -> Timeout: firewall o red. En Render free solo funciona el pooler (IPv4).")
        elif "SSL" in msg:
            print("  -> Problema de SSL: comprueba que la URL termina en ?sslmode=require")
        else:
            print(f"  -> {msg.splitlines()[0][:200]}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
import os
import base64
import hashlib
import logging
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Obtener la llave de cifrado del .env
def _is_development_environment() -> bool:
    is_render = os.getenv("RENDER", "").lower() in ("true", "1")
    if is_render:
        return False
    env = os.getenv("ENVIRONMENT", "production").lower()
    return env in ("development", "dev", "local", "test")


def _is_production_environment() -> bool:
    """True salvo que el entorno se declare explícitamente como desarrollo local."""
    return not _is_development_environment()


# Esquemas de conexión SQL permitidos (allowlist). Cualquier otro (`sqlite:///`,
# `file://`, `duckdb://`…) permitiría leer archivos locales en lugar de una BD remota.
ALLOWED_SQL_SCHEMES = {
    "postgres", "postgresql", "postgresql+psycopg2", "postgresql+psycopg",
    "mysql", "mysql+pymysql", "mariadb", "mariadb+pymysql",
    "mssql", "mssql+pyodbc", "oracle", "oracle+oracledb",
}

ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

if not ENCRYPTION_KEY:
    if not _is_development_environment():
        raise RuntimeError(
            "CRITICAL SECURITY ERROR: 'ENCRYPTION_KEY' no está configurada en entorno de producción. "
            "El servidor no puede arrancar sin clave de cifrado persistente. "
            "Genera una clave con: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    logger.warning(
        "ENCRYPTION_KEY no configurada en entorno de desarrollo. "
        "Usando clave determinista de desarrollo local para evitar corrupción entre reinicios."
    )
    ENCRYPTION_KEY = base64.urlsafe_b64encode(hashlib.sha256(b"vektra-bi-dev-local-key").digest()).decode()

# Si la variable existe pero NO es una clave Fernet válida, el import de este
# módulo reventaba y tumbaba TODO el backend (no solo el cifrado). En su lugar se
# deriva una clave válida y estable a partir del valor proporcionado: el servicio
# arranca y la llave no cambia entre reinicios, así que las API keys ya cifradas
# siguen siendo descifrables. Sigue siendo necesario corregir la variable: el valor
# derivado no es reversible ni auditable desde el panel.
try:
    cipher_suite = Fernet(ENCRYPTION_KEY.encode())
except Exception as e:
    _raw = ENCRYPTION_KEY
    logger.critical(
        "ENCRYPTION_KEY mal formada (%s). Se esperaba una clave Fernet: 44 caracteres "
        "base64url terminados en '='. Genera una con: "
        "python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\". "
        "Mientras tanto se deriva una clave estable (SHA-256) del valor actual.",
        type(e).__name__
    )
    ENCRYPTION_KEY = base64.urlsafe_b64encode(hashlib.sha256(_raw.encode()).digest()).decode()
    cipher_suite = Fernet(ENCRYPTION_KEY.encode())

def encrypt_key(api_key: str) -> str:
    """Cifra una API Key para guardarla en la base de datos."""
    if not api_key: return None
    try:
        # Si ya parece estar cifrada (por el prefijo gcm o similar), no re-cifrar
        # Fernet produce tokens que empiezan con 'gAAAAA'
        if api_key.startswith("gAAAA"): return api_key
        
        encrypted_text = cipher_suite.encrypt(api_key.encode())
        return encrypted_text.decode()
    except Exception as e:
        logger.error("Error al cifrar clave (tipo=%s)", type(e).__name__)
        raise ValueError("Error al cifrar clave: no se permite persistir claves en texto plano.")

def decrypt_key(encrypted_key: str) -> str:
    """Descifra una API Key para usarla en el motor de IA."""
    if not encrypted_key: return None
    try:
        # Solo intentar descifrar si tiene formato de Fernet
        if not encrypted_key.startswith("gAAAA"):
            logger.warning("Intento de descifrar una clave que no tiene formato Fernet (gAAAA).")
            return None
        
        decrypted_text = cipher_suite.decrypt(encrypted_key.encode())
        return decrypted_text.decode()
    except Exception as e:
        logger.error("Error al descifrar clave (tipo=%s)", type(e).__name__)
        return None


def encrypt_file(source_path: str, dest_path: str) -> bool:
    """Cifra un archivo completo con Fernet y lo escribe en dest_path.
    
    Usa un archivo temporal para garantizar atomicidad: si algo falla,
    el archivo original no queda corrupto.
    """
    import tempfile, shutil, os as _os
    tmp_dest = dest_path + ".encrypting"
    try:
        with open(source_path, 'rb') as f:
            data = f.read()
        encrypted = cipher_suite.encrypt(data)
        with open(tmp_dest, 'wb') as f:
            f.write(encrypted)
        # Mover atómicamente solo si todo fue bien
        shutil.move(tmp_dest, dest_path)
        return True
    except Exception as e:
        logger.error("Error cifrando archivo %s (tipo=%s)", source_path, type(e).__name__)
        if _os.path.exists(tmp_dest):
            _os.remove(tmp_dest)
        return False


def encrypt_bytes(data: bytes) -> bytes:
    """Cifra bytes en memoria con Fernet y retorna los bytes cifrados.

    Nunca escribe el contenido en claro en disco. Útil para subir archivos
    directamente cifrados sin pasar por un temporal legible.
    """
    return cipher_suite.encrypt(data)


def validate_external_url_host(url: str) -> None:
    """Valida que la URL (ej. conexión SQLAlchemy) no apunte a hosts internos/privados.

    Mitiga SSRF con tres capas:
      1. Solo esquemas de red explícitamente permitidos (nada de `sqlite:///` o `file://`).
      2. En producción, `ALLOWED_SQL_HOSTS` es obligatoria (fail-closed): sin allowlist no
         se permiten conexiones salientes, para que un despliegue mal configurado no quede
         expuesto a SSRF por defecto.
      3. Se validan **todas** las direcciones que devuelve el DNS (no solo la primera) y se
         rechaza cualquier IP privada, loopback, link-local, reservada, multicast o sin
         especificar.
    Raises ValueError si la URL no es válida o no pasa el filtro.
    """
    import ipaddress
    from urllib.parse import urlparse
    import socket

    parsed = urlparse(url)
    scheme = (parsed.scheme or "").lower()
    if scheme not in ALLOWED_SQL_SCHEMES:
        raise ValueError(
            f"Esquema '{scheme or '(vacío)'}' no permitido. Usa uno de: "
            f"{', '.join(sorted(ALLOWED_SQL_SCHEMES))}."
        )

    host = parsed.hostname
    if not host:
        raise ValueError("URL sin host válido.")

    allowed = [h.strip().lower() for h in os.getenv("ALLOWED_SQL_HOSTS", "").split(",") if h.strip()]
    if allowed:
        if host.lower() not in allowed:
            raise ValueError(f"El host '{host}' no está en la lista de hosts permitidos (ALLOWED_SQL_HOSTS).")
        # Un host explícitamente autorizado por el operador se acepta tal cual.
        return

    if _is_production_environment():
        raise ValueError(
            "Las conexiones SQL externas están deshabilitadas: configura ALLOWED_SQL_HOSTS "
            "con los hosts autorizados."
        )

    blocked_names = {"localhost", "localhost.localdomain"}
    if host.lower() in blocked_names:
        raise ValueError("No se permiten conexiones a hosts locales.")

    # Resolver TODAS las direcciones (A y AAAA): un solo registro privado basta para bloquear.
    try:
        addr_info = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
    except Exception as e:
        raise ValueError(f"No se pudo resolver el host: {type(e).__name__}")

    ips = {info[4][0].split("%")[0] for info in addr_info if info[4]}
    if not ips:
        raise ValueError("El host no resolvió a ninguna dirección IP.")

    for ip_str in ips:
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            raise ValueError(f"Dirección IP no válida devuelta por el DNS: {ip_str}")
        if (ip.is_private or ip.is_loopback or ip.is_link_local or
                ip.is_reserved or ip.is_multicast or ip.is_unspecified):
            raise ValueError("No se permiten conexiones a direcciones IP privadas, locales o reservadas.")


def decrypt_file_to_bytes(file_path: str) -> bytes:
    """Descifra un archivo cifrado con Fernet y retorna los bytes en claro.

    El descifrado ocurre en memoria (RAM): nunca se escribe el contenido
    descifrado a disco, protegiendo los datos del cliente.
    Raises Exception si el archivo no puede descifrarse.
    """
    with open(file_path, 'rb') as f:
        data = f.read()
    return cipher_suite.decrypt(data)

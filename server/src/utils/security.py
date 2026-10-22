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

    Mitiga SSRF: rechaza loopback, RFC1918, link-local, metadata cloud y
    cualquier host que no esté en la allowlist opcional ALLOWED_SQL_HOSTS.
    Raises ValueError si la URL no es válida.
    """
    import ipaddress
    from urllib.parse import urlparse
    import socket

    parsed = urlparse(url)
    host = parsed.hostname
    if not host:
        raise ValueError("URL sin host válido.")

    allowed = [h.strip().lower() for h in os.getenv("ALLOWED_SQL_HOSTS", "").split(",") if h.strip()]
    if allowed:
        if host.lower() not in allowed:
            raise ValueError(f"El host '{host}' no está en la lista de hosts permitidos (ALLOWED_SQL_HOSTS).")
        return

    blocked_names = {"localhost", "localhost.localdomain"}
    if host.lower() in blocked_names:
        raise ValueError("No se permiten conexiones a hosts locales.")

    # Resolver a IP y bloquear rangos privados
    try:
        addr_info = socket.getaddrinfo(host, None)
        ip = ipaddress.ip_address(addr_info[0][4][0])
    except Exception as e:
        raise ValueError(f"No se pudo resolver el host: {type(e).__name__}")

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

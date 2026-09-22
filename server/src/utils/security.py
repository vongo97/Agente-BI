import os
import logging
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Obtener la llave de cifrado del .env
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

if not ENCRYPTION_KEY:
    # Generar una temporal si no existe para evitar crash, pero loggear advertencia crítica
    msg = (
        "\n"
        "========================================================================\n"
        "🚨 ADVERTENCIA CRÍTICA DE PERSISTENCIA Y SEGURIDAD 🚨\n"
        "La variable de entorno 'ENCRYPTION_KEY' no está configurada en el archivo .env.\n"
        "Se ha generado una llave temporal aleatoria para evitar que el servidor se caiga.\n"
        "\n"
        "👉 IMPACTO: Cada vez que el servidor se reinicie (ej. hibernación de Render/despliegues),\n"
        "   esta llave temporal CAMBIARÁ. Todas las API Keys guardadas en la base de datos\n"
        "   cifradas anteriormente se volverán INSERVIBLES y los usuarios recibirán errores.\n"
        "\n"
        "👉 SOLUCIÓN: Genera una llave estática ejecutando:\n"
        "   python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"\n"
        "   Y agrégala a tu .env o al Dashboard de Render como ENCRYPTION_KEY=<valor>\n"
        "========================================================================\n"
    )
    logger.warning(msg)
    ENCRYPTION_KEY = Fernet.generate_key().decode()

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
        return api_key

def decrypt_key(encrypted_key: str) -> str:
    """Descifra una API Key para usarla en el motor de IA."""
    if not encrypted_key: return None
    try:
        # Solo intentar descifrar si tiene formato de Fernet
        if not encrypted_key.startswith("gAAAA"): return encrypted_key
        
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


def decrypt_file_to_bytes(file_path: str) -> bytes:
    """Descifra un archivo cifrado con Fernet y retorna los bytes en claro.
    
    El descifrado ocurre en memoria (RAM): nunca se escribe el contenido
    descifrado a disco, protegiendo los datos del cliente.
    Raises Exception si el archivo no puede descifrarse.
    """
    with open(file_path, 'rb') as f:
        data = f.read()
    return cipher_suite.decrypt(data)

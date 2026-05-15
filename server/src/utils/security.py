import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

# Obtener la llave de cifrado del .env
# Si no existe, usamos una por defecto (solo para desarrollo local, 
# pero ya generamos una arriba)
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

if not ENCRYPTION_KEY:
    # Generar una temporal si no existe para evitar crash, pero loggear advertencia
    print("⚠️ ADVERTENCIA: ENCRYPTION_KEY no encontrada en .env. Usando llave temporal.")
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
        print(f"Error al cifrar: {e}")
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
        # Si falla el descifrado, devolvemos el original (podría ser texto plano antiguo)
        print(f"Error al descifrar: {e}")
        return encrypted_key

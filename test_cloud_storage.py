import os
import sys
from dotenv import load_dotenv

# Añadir el path del servidor para poder importar módulos
sys.path.append(os.path.join(os.getcwd(), 'server'))

# Forzar carga de variables de entorno
load_dotenv('server/.env')

from src.utils.supabase_storage import upload_file_to_cloud, download_file_from_cloud, sync_cloud_to_local

def test_storage():
    print("--- INICIANDO TEST DE SUPABASE STORAGE ---")
    
    # 1. Crear un archivo de prueba
    test_file = "test_cloud_sync.txt"
    with open(test_file, "w") as f:
        f.write("Esta es una prueba de persistencia en la nube para Agente BI.")
    
    # 2. Subir a la nube
    print(f"Subiendo {test_file} a Supabase...")
    remote_name = "tests/test_file.txt"
    success = upload_file_to_cloud(test_file, remote_name)
    
    if not success:
        print("[FALLO] No se pudo subir el archivo. Revisa las credenciales y que el bucket 'bi_storage' exista en Supabase.")
        return

    print("[EXITO] Archivo subido.")

    # 3. Eliminar localmente
    os.remove(test_file)
    print("Archivo local eliminado para probar la descarga.")

    # 4. Intentar descargar
    print("Descargando desde Supabase...")
    download_success = download_file_from_cloud(remote_name, test_file)
    
    if download_success:
        print("[EXITO] Archivo recuperado de la nube.")
        with open(test_file, "r") as f:
            content = f.read()
            print(f"Contenido recuperado: {content}")
    else:
        print("[FALLO] No se pudo descargar el archivo.")

    # Limpieza
    if os.path.exists(test_file):
        os.remove(test_file)

if __name__ == "__main__":
    test_storage()

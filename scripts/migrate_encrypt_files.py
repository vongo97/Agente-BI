"""
Script de migración: cifra archivos existentes de clientes.

Ejecución (una sola vez tras el deploy del código nuevo):
    python scripts/migrate_encrypt_files.py

Requisitos:
    - La variable ENCRYPTION_KEY debe estar en el .env o en el entorno.
    - La base de datos debe tener la columna is_encrypted (se agrega automáticamente
      en init_db() al arrancar el servidor).
"""
import os
import sys
import logging

# Agregar la raíz del servidor al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'server'))

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("migrate_encrypt")


def main():
    from src.database import SessionLocal, DataSource
    from src.utils.security import encrypt_file

    db = SessionLocal()
    try:
        # Obtener todas las fuentes de archivo NO cifradas
        sources = db.query(DataSource).filter(
            DataSource.type == "file",
            (DataSource.is_encrypted == False) | (DataSource.is_encrypted == None)
        ).all()

        total = len(sources)
        if total == 0:
            logger.info("No hay archivos pendientes de cifrar. Todo ya esta al dia.")
            return

        logger.info("Encontrados %d archivos para cifrar...", total)
        migrated = 0
        skipped = 0
        failed = 0

        for source in sources:
            file_path = source.url
            if not file_path or not os.path.exists(file_path):
                logger.warning("Archivo no encontrado en disco: %s (source_id=%s) - omitido.", file_path, source.id)
                skipped += 1
                continue

            logger.info("Cifrando: %s (source_id=%s, user=%s)", os.path.basename(file_path), source.id, source.user_id)
            ok = encrypt_file(file_path, file_path)

            if ok:
                source.is_encrypted = True
                db.commit()
                migrated += 1
                logger.info("  OK: Cifrado y DB actualizada.")
            else:
                failed += 1
                logger.error("  ERROR: Fallo el cifrado de %s", file_path)

        logger.info("")
        logger.info("=== Migracion completada ===")
        logger.info("  Cifrados:  %d / %d", migrated, total)
        logger.info("  Omitidos:  %d (archivo no encontrado en disco)", skipped)
        logger.info("  Fallidos:  %d", failed)

        if failed > 0:
            logger.warning("Algunos archivos NO fueron cifrados. Revisa los logs arriba.")
        else:
            logger.info("Todos los archivos fueron cifrados correctamente.")

    finally:
        db.close()


if __name__ == "__main__":
    main()

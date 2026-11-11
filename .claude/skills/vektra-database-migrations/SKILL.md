---
name: vektra-database-migrations
description: Gestión de esquemas y migraciones de bases de datos con Alembic. Úsalo cuando modifiques database.py, agregues nuevos modelos SQLAlchemy o realices cambios de esquema.
---

# Vektra Database Migrations

Este documento describe el flujo estricto y las reglas de diseño para modificar el esquema de base de datos en Vektra BI.

## Flujo de Migración con Alembic

1. **Prohibición de Alteraciones Manuales:**
   - **Queda estrictamente prohibido** ejecutar sentencias `ALTER TABLE` manuales o inline dentro de los scripts de inicialización del servidor (como `database.py`).
   - Todos los cambios estructurales deben documentarse mediante archivos de migración autogenerados de Alembic:
     `alembic revision --autogenerate -m "nombre_de_migracion"`

2. **Revisión del Script Autogenerado:**
   - Revisa siempre el script generado bajo `migrations/versions/` antes de aplicarlo, asegurando que los índices, restricciones de unicidad y claves foráneas se creen de manera correcta.

---

## Compatibilidad Dev vs Prod (SQLite ➔ PostgreSQL)

1. **Tipos de Datos Compatibles:**
   - Evita tipos de datos propietarios o comportamientos específicos que solo funcionen en SQLite.
   - En SQLite las fechas se guardan como cadenas; en PostgreSQL como objetos `DateTime` nativos. Usa tipos genéricos de SQLAlchemy (`SQLAlchemy.DateTime` con `timezone=True`).

2. **Tratamiento de Claves Foráneas:**
   - Garantizar que las restricciones de clave foránea estén soportadas y habilitadas en desarrollo (`PRAGMA foreign_keys = ON;` para SQLite) para replicar el comportamiento de PostgreSQL de producción.

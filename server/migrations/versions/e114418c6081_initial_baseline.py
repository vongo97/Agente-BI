"""Initial baseline

Revision ID: e114418c6081
Revises:
Create Date: 2026-05-15 14:02:35.327662

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e114418c6081'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _ensure_tables_exist() -> None:
    """Crea el esquema si la base de datos está vacía.

    P-19: la revisión asumía que las tablas ya existían (las creaba
    `init_db()` con `create_all()`), así que sobre una BD **limpia** el
    `op.drop_constraint` reventaba con
    `NotImplementedError: No support for ALTER of constraints in SQLite dialect`.

    `create_all` es un no-op si las tablas ya existen, así que en el Postgres de
    Render (donde esta revisión YA corrió) esta llamada no cambia nada: el
    comportamiento para una base ya migrada es idéntico al de antes.
    """
    from src.database import Base
    from src.database import engine

    Base.metadata.create_all(bind=engine)


def _tables_exist() -> bool:
    """True si la tabla `dashboard_items` ya existe en la BD conectada."""
    from src.database import engine

    inspector = sa.inspect(engine)
    return "dashboard_items" in inspector.get_table_names()


def _sqlite_fks_already_cascade() -> bool:
    """True si en SQLite las FK de `dashboard_items` ya tienen ON DELETE CASCADE.

    SQLite **no nombra** sus claves foráneas (`name = None`), así que
    `op.drop_constraint(None, ...)` no puede funcionar ni con batch mode.
    Alembic no puede reemplazar una FK sin nombre, así que no se intenta:
    se comprueba si el estado deseado ya está y, si lo está, no se toca nada.
    """
    from src.database import engine

    inspector = sa.inspect(engine)
    try:
        fks = inspector.get_foreign_keys("dashboard_items")
    except Exception:
        return False
    if not fks:
        return False
    return all(
        (fk.get("options") or {}).get("ondelete", "").upper() == "CASCADE"
        for fk in fks
    )


def _column_exists(table: str, column: str) -> bool:
    """True si la columna ya existe en la tabla (para que la revisión sea idempotente)."""
    from src.database import engine

    inspector = sa.inspect(engine)
    try:
        return column in {c["name"] for c in inspector.get_columns(table)}
    except Exception:
        return False


def upgrade() -> None:
    """Upgrade schema."""
    # P-19: sobre una BD limpia no hay tablas que alterar; se crean primero.
    _ensure_tables_exist()

    if _tables_exist():
        # Las FK de `dashboard_items` se recrean con ON DELETE CASCADE.
        # En SQLite no se pueden tocar (no tienen nombre), pero `create_all`
        # ya las crea con CASCADE, así que el estado deseado se cumple.
        if not _sqlite_fks_already_cascade():
            op.drop_constraint(None, 'dashboard_items', type_='foreignkey')
            op.drop_constraint(None, 'dashboard_items', type_='foreignkey')
            op.create_foreign_key(None, 'dashboard_items', 'chats', ['chat_id'], ['id'], ondelete='CASCADE')
            op.create_foreign_key(None, 'dashboard_items', 'messages', ['message_id'], ['id'], ondelete='CASCADE')

    # P-19: `create_all` ya crea `current_round`, así que añadirla otra vez
    # falla con "duplicate column name". La revisión debe ser idempotente:
    # se añade solo si falta.
    if not _column_exists('simulations', 'current_round'):
        op.add_column('simulations', sa.Column('current_round', sa.Integer(), nullable=True))

    # P-19: `ALTER COLUMN ... TYPE` no existe en SQLite. `batch_alter_table` lo
    # resuelve con la estrategia "copy-and-move" (recrea la tabla copiando los
    # datos). En PostgreSQL el batch mode no altera el SQL emitido.
    with op.batch_alter_table('user_configs') as batch_op:
        batch_op.alter_column('preferred_provider',
                   existing_type=sa.TEXT(),
                   type_=sa.String(),
                   existing_nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('user_configs', 'preferred_provider',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               existing_nullable=True)
    op.drop_column('simulations', 'current_round')
    if _tables_exist():
        op.drop_constraint(None, 'dashboard_items', type_='foreignkey')
        op.drop_constraint(None, 'dashboard_items', type_='foreignkey')
        op.create_foreign_key(None, 'dashboard_items', 'messages', ['message_id'], ['id'])
        op.create_foreign_key(None, 'dashboard_items', 'chats', ['chat_id'], ['id'])

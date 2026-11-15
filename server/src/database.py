from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, DateTime, Float, Boolean, Table, text, inspect
from sqlalchemy.orm import sessionmaker, relationship, DeclarativeBase
from datetime import datetime
import os
import re
import logging

logger = logging.getLogger(__name__)

# Configuración de la base de datos
DB_URL = os.getenv("DATABASE_URL", "sqlite:///./bi_agent.db")

def sanitize_db_error(msg: str) -> str:
    """Enmascara contraseñas y credenciales de URLs de bases de datos dentro de mensajes de error.

    P-19: el usuario **no** es un secreto; la contraseña sí. Por eso el
    enmascarado conserva el usuario (`usuario:***@host`): se puede leer *qué*
    usuario falló sin filtrar la contraseña.
    """
    if not msg:
        return ""
    # Enmascarar contraseñas en URLs de tipo dialect+driver://user:password@host:port/db
    sanitized = re.sub(r'([a-zA-Z0-9+.-]+://)([^:@/]+):([^@/]+)@', r'\1\2:***@', msg)
    # Por si hay URLs SQL sin dialecto (ej: user:password@host).
    # Ni el usuario ni la contraseña pueden contener '/' (sería parte de una URL
    # con esquema, ya tratada arriba) ni '*' (sería una credencial ya
    # enmascarada: no hay que enmascarar dos veces, o el usuario acabaría comido).
    sanitized = re.sub(r'(?<![a-zA-Z0-9+.\-*/])([^:@/\s*]+):([^@/\s*]+)@([a-zA-Z0-9.-]+)', r'\1:***@\3', sanitized)
    return sanitized

# Limpieza básica de la URL
if DB_URL:
    DB_URL = DB_URL.replace("\n", "").replace("\r", "").strip().strip('"').strip("'")
    if DB_URL.startswith("psql "):
        DB_URL = DB_URL.replace("psql ", "", 1).strip().strip("'").strip('"')
    DB_URL = DB_URL.replace(" ", "")

if DB_URL.startswith("postgres://"):
    DB_URL = DB_URL.replace("postgres://", "postgresql://", 1)

# Crear Engine
# P-19: una `DATABASE_URL` inválida NO puede caerse a SQLite en silencio. Con el
# fallback, un Postgres mal configurado arrancaba "bien" y el servicio quedaba
# guardando chats y claves en un SQLite efímero: los datos se perdían en cada
# deploy y los usuarios veían un 500 al leer su configuración.
# Ahora el arranque es fail-closed: si la URL está mal formada, se aborta con un
# mensaje claro. Si la URL es válida pero el servidor no responde, se aborta
# también (ver `_assert_database_reachable`), salvo en desarrollo local.
def _is_production() -> bool:
    """True si el entorno NO se declara explicitamente como desarrollo.

    Mismo criterio que `is_development_mode()`: la ausencia de configuración
    se interpreta como producción (fail-closed), nunca al revés.
    """
    return os.getenv("ENVIRONMENT", "production").strip().lower() not in {
        "development",
        "dev",
        "local",
        "test",
    }


def _build_engine(url: str):
    """Construye el engine. Lanza si la URL no es utilizable como URL de BD."""
    if "sqlite" in url:
        return create_engine(url, connect_args={"check_same_thread": False})
    return create_engine(
        url,
        connect_args={"connect_timeout": 10},
        pool_pre_ping=True,
        pool_recycle=300
    )


try:
    engine = _build_engine(DB_URL)
except Exception as e:
    # P-19: la URL está mal formada (o falta el driver). Abortar es lo correcto:
    # arrancar con otra base de datos es peor que no arrancar, porque el
    # servicio "parece" sano mientras pierde datos.
    raise RuntimeError(
        "DATABASE_URL inválida: no se pudo crear el engine de base de datos "
        f"({sanitize_db_error(str(e))}). Arranque abortado: no se usa un "
        "fallback a SQLite porque los datos se perderían en el siguiente deploy."
    ) from e


def _assert_database_reachable() -> None:
    """Verifica que la BD responde ANTES de aceptar tráfico.

    `create_engine()` es perezoso: no abre ninguna conexión, así que una URL
    bien formada pero con un host inexistente no falla aquí, sino en la
    primera petición (o peor, a los pocos minutos). P-19 pide que el arranque
    aborte cuando la `DATABASE_URL` es inválida; "inválida" incluye "inalcanzable".

    En desarrollo local se permite continuar (el developer puede estar levantando
    la BD después); en producción el arranque aborta.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        message = sanitize_db_error(str(exc))
        if _is_production():
            raise RuntimeError(
                "DATABASE_URL configurada pero la base de datos no responde "
                f"({message}). Arranque abortado: no se degrada a SQLite porque "
                "los datos del usuario se perderían al reiniciar."
            ) from exc
        logger.warning(
            "ATENCIÓN: la base de datos configurada no responde (%s). Se continúa "
            "en modo desarrollo; en producción esto abortaría el arranque.",
            message,
        )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def db_diagnostic() -> dict:
    """Información segura del engine para diagnóstico (sin host ni credenciales).
    'dialect' permite saber desde fuera si los datos son persistentes (postgres)
    o efímeros (SQLite en el contenedor, que se borra en cada deploy)."""
    dialect = engine.dialect.name
    return {
        "dialect": dialect,
        "persistent": dialect not in ("sqlite",),
    }


def db_schema_diagnostic() -> dict:
    """Comprueba que las columnas requeridas por /upload existen.

    No expone datos ni credenciales: solo nombres de columnas ya públicos en
    el código. Sirve para distinguir un 500 de esquema de un fallo de archivo.
    """
    required = {"is_encrypted", "size_bytes"}
    try:
        columns = {column["name"] for column in inspect(engine).get_columns("data_sources")}
    except Exception as exc:
        logger.warning("No se pudo inspeccionar data_sources: %s", sanitize_db_error(str(exc)))
        return {"upload_schema_ready": None}
    return {
        "upload_schema_ready": required.issubset(columns),
    }

# Aviso temprano: en Render el disco es efímero, así que SQLite significa perder
# chats, fuentes y configuración guardada en cada reinicio.
_db_info = db_diagnostic()
if not _db_info["persistent"]:
    logger.warning(
        "CONFIG: usando SQLite (%s). Los datos NO sobreviven a un reinicio/deploy. "
        "Define DATABASE_URL (PostgreSQL) en el panel del servicio para tener persistencia.",
        DB_URL.split("///")[-1] if "///" in DB_URL else DB_URL
    )
else:
    logger.info("CONFIG: base de datos %s (persistente)", _db_info["dialect"])

class Base(DeclarativeBase):
    """Base de SQLAlchemy 2.0"""
    pass


chat_data_sources = Table(
    "chat_data_sources",
    Base.metadata,
    Column("chat_id", Integer, ForeignKey("chats.id", ondelete="CASCADE"), primary_key=True),
    Column("data_source_id", Integer, ForeignKey("data_sources.id", ondelete="CASCADE"), primary_key=True),
    Column("created_at", DateTime, default=datetime.utcnow, nullable=False),
)

class Chat(Base):
    __tablename__ = "chats"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    title = Column(String)
    data_source_id = Column(Integer, ForeignKey("data_sources.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")
    dashboard_items = relationship("DashboardItem", back_populates="chat")
    data_source = relationship("DataSource", back_populates="primary_chats", foreign_keys=[data_source_id])
    data_sources = relationship(
        "DataSource",
        secondary=chat_data_sources,
        back_populates="chats",
        order_by="DataSource.id",
    )

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id"))
    role = Column(String)
    content = Column(Text)
    figure_json = Column(Text, nullable=True)
    analysis_code = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    chat = relationship("Chat", back_populates="messages")
    dashboard_item = relationship("DashboardItem", back_populates="message", uselist=False)

class UserConfig(Base):
    __tablename__ = "user_configs"
    user_id = Column(String, primary_key=True, index=True)
    gemini_key = Column(String, nullable=True)
    mistral_key = Column(String, nullable=True)
    gamma_key = Column(String, nullable=True)
    groq_key = Column(String, nullable=True)
    # Nuevos proveedores (ver src/engine/providers.py). Se guardan cifrados igual
    # que los anteriores, nunca en claro ni en el frontend.
    openai_key = Column(String, nullable=True)
    anthropic_key = Column(String, nullable=True)
    deepseek_key = Column(String, nullable=True)
    openrouter_key = Column(String, nullable=True)
    nvidia_key = Column(String, nullable=True)
    # Modelo elegido por el usuario por proveedor, en JSON: {"nvidia": "moonshotai/kimi-k3"}
    provider_models = Column(Text, nullable=True)
    preferred_provider = Column(String, default="gemini")
    temperature = Column(Float, default=0.2, nullable=True)
    anomaly_sensitivity = Column(Float, default=2.5, nullable=True)
    magic_clean_strategy = Column(String, default="remove", nullable=True)
    currency_format = Column(String, default="USD", nullable=True)
    date_format = Column(String, default="DD/MM/YYYY", nullable=True)
    brand_color = Column(String, default="#2dd4bf", nullable=True)
    brand_logo_url = Column(String, nullable=True)
    report_org_name = Column(String, default="VEKTRA BI", nullable=True)
    report_footer_text = Column(String, default="Confidencial - Solo uso interno", nullable=True)
    pdf_orientation = Column(String, default="portrait", nullable=True)
    pdf_include_data_table = Column(Boolean, default=True, nullable=True)
    chart_theme = Column(String, default="neon", nullable=True)
    # Columnas para PKCE OAuth2
    code_verifier = Column(String, nullable=True)
    code_verifier_expires = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class DashboardItem(Base):
    __tablename__ = "dashboard_items"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id", ondelete="CASCADE"))
    message_id = Column(Integer, ForeignKey("messages.id", ondelete="CASCADE"))
    pinned_at = Column(DateTime, default=datetime.utcnow)
    
    chat = relationship("Chat", back_populates="dashboard_items")
    message = relationship("Message", back_populates="dashboard_item")

class DataSource(Base):
    __tablename__ = "data_sources"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    name = Column(String)
    type = Column(String)
    url = Column(Text)
    columns = Column(Text, nullable=True)
    is_encrypted = Column(Boolean, default=False, nullable=True)
    size_bytes = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    primary_chats = relationship("Chat", back_populates="data_source", foreign_keys="Chat.data_source_id")
    chats = relationship("Chat", secondary=chat_data_sources, back_populates="data_sources")

class Simulation(Base):
    __tablename__ = "simulations"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    title = Column(String)
    hypothesis = Column(Text)
    data_source_id = Column(Integer, ForeignKey("data_sources.id"), nullable=True)
    result_report = Column(Text, nullable=True)
    status = Column(String, default="pending")
    provider = Column(String, default="gemini")
    current_round = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

    agents = relationship("SimulationAgent", back_populates="simulation", cascade="all, delete-orphan")
    messages = relationship("SimulationMessage", back_populates="simulation", cascade="all, delete-orphan")

class SimulationAgent(Base):
    __tablename__ = "simulation_agents"
    id = Column(Integer, primary_key=True, index=True)
    simulation_id = Column(Integer, ForeignKey("simulations.id"))
    name = Column(String)
    role = Column(String)
    description = Column(Text)
    personality = Column(Text)
    stance = Column(String, nullable=True)

    simulation = relationship("Simulation", back_populates="agents")
    messages = relationship("SimulationMessage", back_populates="agent")

class SimulationMessage(Base):
    __tablename__ = "simulation_messages"
    id = Column(Integer, primary_key=True, index=True)
    simulation_id = Column(Integer, ForeignKey("simulations.id"))
    agent_id = Column(Integer, ForeignKey("simulation_agents.id"), nullable=True)
    round_number = Column(Integer)
    content = Column(Text)
    sentiment = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    simulation = relationship("Simulation", back_populates="messages")
    agent = relationship("SimulationAgent", back_populates="messages")

def _ensure_columns(table: str, columns: list[tuple[str, str]]) -> None:
    """Agrega columnas faltantes sin abortar las migraciones siguientes.

    Un ``ALTER TABLE`` que falla porque la columna ya existe deja la
    transacción abortada en PostgreSQL; si se reutiliza la misma conexión,
    las columnas posteriores nunca se agregan. Por eso se inspecciona el
    esquema y cada ALTER se ejecuta en su propia transacción.
    """
    try:
        existing = {column["name"] for column in inspect(engine).get_columns(table)}
    except Exception as exc:
        logger.warning(
            "No se pudo inspeccionar la tabla %s: %s",
            table,
            sanitize_db_error(str(exc)),
        )
        return

    for column, column_type in columns:
        if column in existing:
            continue
        try:
            with engine.begin() as conn:
                conn.execute(
                    text(f"ALTER TABLE {table} ADD COLUMN {column} {column_type};")
                )
            logger.info("Migrada DB: columna %s añadida a %s.", column, table)
        except Exception as exc:
            logger.warning(
                "No se pudo migrar %s.%s: %s",
                table,
                column,
                sanitize_db_error(str(exc)),
            )


def init_db():
    """Crea las tablas y agrega las columnas nuevas de forma idempotente.

    P-19: si la BD configurada no responde, el arranque aborta (fail-closed).
    Un servicio que arranca contra una BD caída parece sano y falla en la
    primera petición de cada usuario.
    """
    _assert_database_reachable()

    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Tablas sincronizadas con Base.metadata.create_all")

        _ensure_columns(
            "data_sources",
            [
                ("is_encrypted", "BOOLEAN DEFAULT FALSE"),
                ("size_bytes", "INTEGER"),
            ],
        )
        _ensure_columns(
            "user_configs",
            [
                ("groq_key", "VARCHAR"),
                ("openai_key", "VARCHAR"),
                ("anthropic_key", "VARCHAR"),
                ("deepseek_key", "VARCHAR"),
                ("openrouter_key", "VARCHAR"),
                ("nvidia_key", "VARCHAR"),
                ("provider_models", "TEXT"),
                ("temperature", "FLOAT"),
                ("anomaly_sensitivity", "FLOAT"),
                ("magic_clean_strategy", "VARCHAR"),
                ("currency_format", "VARCHAR"),
                ("date_format", "VARCHAR"),
                ("brand_color", "VARCHAR"),
                ("brand_logo_url", "VARCHAR"),
                ("report_org_name", "VARCHAR"),
                ("report_footer_text", "VARCHAR"),
                ("pdf_orientation", "VARCHAR"),
                ("pdf_include_data_table", "BOOLEAN"),
                ("chart_theme", "VARCHAR"),
            ],
        )
    except Exception as e:
        logger.error("ERROR en init_db: %s", sanitize_db_error(str(e)))
        if _is_production():
            # P-19: el esquema no se pudo sincronizar. Continuar serviría datos
            # con un esquema desfasado (el drift que provocó el 500 en
            # /user-config). Es preferible no arrancar.
            raise RuntimeError(
                "No se pudo inicializar el esquema de base de datos "
                f"({sanitize_db_error(str(e))}). Arranque abortado."
            ) from e


def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error("Error en sesión de DB: %s", sanitize_db_error(str(e)))
        raise
    finally:
        db.close()

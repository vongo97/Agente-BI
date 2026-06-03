from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, DateTime, text
from sqlalchemy.orm import sessionmaker, relationship, DeclarativeBase
from datetime import datetime
import os
import re
import logging

logger = logging.getLogger(__name__)

# Configuración de la base de datos
DB_URL = os.getenv("DATABASE_URL", "sqlite:///./bi_agent.db")

def sanitize_db_error(msg: str) -> str:
    """Enmascara contraseñas y credenciales de URLs de bases de datos dentro de mensajes de error."""
    if not msg:
        return ""
    # Enmascarar contraseñas en URLs de tipo dialect+driver://user:password@host:port/db
    sanitized = re.sub(r'([a-zA-Z0-9+.-]+://)([^:]+):([^@]+)@', r'\1\2:***@', msg)
    # Por si hay URLs SQL sin dialecto (ej: user:password@host)
    sanitized = re.sub(r'([^:@]+):([^@]+)@([a-zA-Z0-9.-]+)', r'\1:***@\3', sanitized)
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
try:
    if "sqlite" in DB_URL:
        engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
    else:
        engine = create_engine(DB_URL)
except Exception as e:
    logger.critical("CRITICAL: Fallo al crear engine de DB: %s. Usando SQLite fallback.",
                    sanitize_db_error(str(e)))
    DB_URL = "sqlite:///./bi_agent.db"
    engine = create_engine(DB_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    """Base de SQLAlchemy 2.0"""
    pass

class Chat(Base):
    __tablename__ = "chats"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    title = Column(String)
    data_source_id = Column(Integer, ForeignKey("data_sources.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")
    dashboard_items = relationship("DashboardItem", back_populates="chat")
    data_source = relationship("DataSource", back_populates="chats")

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
    preferred_provider = Column(String, default="gemini")
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
    created_at = Column(DateTime, default=datetime.utcnow)

    chats = relationship("Chat", back_populates="data_source")

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

def init_db():
    """
    Inicializa las tablas. Las migraciones de columnas ahora se delegan a Alembic.
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Tablas sincronizadas con Base.metadata.create_all")
    except Exception as e:
        logger.error("ERROR en init_db: %s", sanitize_db_error(str(e)))

def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error("Error en sesión de DB: %s", sanitize_db_error(str(e)))
        raise
    finally:
        db.close()

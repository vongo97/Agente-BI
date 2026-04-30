from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, DateTime, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

# Configuración de la base de datos
DB_URL = os.getenv("DATABASE_URL", "sqlite:///./bi_agent.db")

# Limpieza básica (quitar psql command, espacios o comillas accidentales)
if DB_URL:
    # Eliminar saltos de línea y espacios accidentales (común al copiar de terminales)
    DB_URL = DB_URL.replace("\n", "").replace("\r", "").strip().strip('"').strip("'")
    if DB_URL.startswith("psql "):
        DB_URL = DB_URL.replace("psql ", "", 1).strip().strip("'").strip('"')
    # Eliminar espacios internos que puedan romper SQLAlchemy
    DB_URL = DB_URL.replace(" ", "")

# Debugging (con máscara para seguridad)
def mask_url(url):
    if "@" in url:
        prefix, suffix = url.split("@", 1)
        if ":" in prefix:
            protocol_user, password = prefix.rsplit(":", 1)
            return f"{protocol_user}:****@{suffix}"
    return url

print(f"DEBUG: Intentando conectar a DB (URL limpia): {mask_url(DB_URL)}")

# Solución para URLs de Render/Heroku que usan postgres:// en vez de postgresql://
if DB_URL.startswith("postgres://"):
    DB_URL = DB_URL.replace("postgres://", "postgresql://", 1)

try:
    engine = create_engine(DB_URL)
    if "sqlite" in DB_URL:
        engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
except Exception as e:
    print(f"CRITICAL ERROR: No se pudo crear el engine de SQLAlchemy: {str(e)}")
    # Fallback to sqlite if postgres fails during development/fix
    print("WARNING: Usando bi_agent.db local como fallback.")
    DB_URL = "sqlite:///./bi_agent.db"
    engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Chat(Base):
    __tablename__ = "chats"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)  # Email del usuario de NextAuth
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
    role = Column(String)  # 'user' o 'assistant'
    content = Column(Text)
    figure_json = Column(Text, nullable=True) # Plotly JSON string
    analysis_code = Column(Text, nullable=True) # Código real generado por la IA
    created_at = Column(DateTime, default=datetime.utcnow)
    chat = relationship("Chat", back_populates="messages")
    dashboard_item = relationship("DashboardItem", back_populates="message", uselist=False)

class UserConfig(Base):
    __tablename__ = "user_configs"
    user_id = Column(String, primary_key=True, index=True) # Email del usuario
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
    type = Column(String) # 'sql', 'gsheets' o 'file'
    url = Column(Text) # URL o Path del archivo
    columns = Column(Text, nullable=True) # JSON con nombres de columnas
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
    status = Column(String, default="pending") # pending, running, completed, error
    provider = Column(String, default="gemini")
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
    stance = Column(String, nullable=True) # Posición inicial ante la hipótesis

    simulation = relationship("Simulation", back_populates="agents")
    messages = relationship("SimulationMessage", back_populates="agent")

class SimulationMessage(Base):
    __tablename__ = "simulation_messages"
    id = Column(Integer, primary_key=True, index=True)
    simulation_id = Column(Integer, ForeignKey("simulations.id"))
    agent_id = Column(Integer, ForeignKey("simulation_agents.id"), nullable=True) # Null si es el narrador/sistema
    round_number = Column(Integer)
    content = Column(Text)
    sentiment = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    simulation = relationship("Simulation", back_populates="messages")
    agent = relationship("SimulationAgent", back_populates="messages")

# Crear tablas y aplicar migraciones manuales de columnas
def init_db():
    try:
        # 1. Crear tablas base si no existen
        Base.metadata.create_all(bind=engine)
        
        # 2. Migración: Añadir columnas faltantes por evolución del modelo
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            # Columna 'columns' en 'data_sources'
            for table, col, col_type in [
                ("data_sources", "columns", "TEXT"),
                ("chats", "data_source_id", "INTEGER"),
                ("messages", "analysis_code", "TEXT"),
                ("user_configs", "preferred_provider", "TEXT"),
                ("simulations", "provider", "TEXT")
            ]:
                try:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"))
                    print(f"COLUMNA OK: '{col}' añadida a '{table}'")
                except Exception as e:
                    if "already exists" not in str(e).lower() and "duplicate column" not in str(e).lower():
                        print(f"AVISO: Error migración {table} ({col}): {e}")
                
    except Exception as e:
        print(f"ERROR en init_db: {str(e)}")
        print("El servidor continuará pero la base de datos podría no estar lista.")

def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        print(f"Error en sesión de DB: {str(e)}")
        raise
    finally:
        db.close()

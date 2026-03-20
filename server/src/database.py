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
    created_at = Column(DateTime, default=datetime.utcnow)
    chat = relationship("Chat", back_populates="messages")
    dashboard_item = relationship("DashboardItem", back_populates="message", uselist=False)

class UserConfig(Base):
    __tablename__ = "user_configs"
    user_id = Column(String, primary_key=True, index=True) # Email del usuario
    gemini_key = Column(String, nullable=True)
    mistral_key = Column(String, nullable=True)
    gamma_key = Column(String, nullable=True)
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

# Crear tablas y aplicar migraciones manuales de columnas
def init_db():
    try:
        # 1. Crear tablas base si no existen
        Base.metadata.create_all(bind=engine)
        
        # 2. Migración: Añadir columnas faltantes por evolución del modelo
        # Usamos una nueva conexión con AUTOCOMMIT para migraciones de esquema
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            # Columna 'columns' en 'data_sources'
            try:
                conn.execute(text("ALTER TABLE data_sources ADD COLUMN columns TEXT"))
                print("✅ Columna 'columns' añadida a 'data_sources'")
            except Exception as e:
                if "already exists" not in str(e).lower() and "duplicate column" not in str(e).lower():
                    print(f"⚠️ Error migracion data_sources (columns): {e}")

            # Columna 'data_source_id' en 'chats'
            try:
                conn.execute(text("ALTER TABLE chats ADD COLUMN data_source_id INTEGER"))
                print("✅ Columna 'data_source_id' añadida a 'chats'")
            except Exception as e:
                # Silenciamos solo errores de "ya existe"
                if "already exists" not in str(e).lower() and "duplicate column" not in str(e).lower():
                    print(f"⚠️ Error migracion chats (data_source_id): {e}")
                
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

from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

# Configuración de la base de datos
DB_URL = os.getenv("DATABASE_URL", "sqlite:///./bi_agent.db")
# Solución para URLs de Render/Heroku que usan postgres:// en vez de postgresql://
if DB_URL.startswith("postgres://"):
    DB_URL = DB_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DB_URL)
if "sqlite" in DB_URL:
    engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Chat(Base):
    __tablename__ = "chats"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)  # Email del usuario de NextAuth
    title = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")
    dashboard_items = relationship("DashboardItem", back_populates="chat")

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

class DashboardItem(Base):
    __tablename__ = "dashboard_items"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id", ondelete="CASCADE"))
    message_id = Column(Integer, ForeignKey("messages.id", ondelete="CASCADE"))
    pinned_at = Column(DateTime, default=datetime.utcnow)
    
    chat = relationship("Chat", back_populates="dashboard_items")
    message = relationship("Message", back_populates="dashboard_item")

# Crear tablas
def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

from sqlalchemy import create_engine, Column, String, DateTime, Boolean, ForeignKey, Text, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

Base = declarative_base()

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = 'users'
    user_id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=func.now())
    last_login = Column(DateTime)
    chats = relationship("Chat", back_populates="user")

class Chat(Base):
    __tablename__ = 'chat'
    chat_id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey('users.user_id'))
    title = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=func.now())
    user = relationship("User", back_populates="chats")
    syllabus = relationship("Syllabus", uselist=False, back_populates="chat")
    textbook = relationship("Textbook", uselist=False, back_populates="chat")
    messages = relationship("ChatMessage", back_populates="chat")
    summaries = relationship("Summary", back_populates="chat")
    mcqs = relationship("MCQ", back_populates="chat")
    diagrams = relationship("Diagram", back_populates="chat")

class Syllabus(Base):
    __tablename__ = 'syllabus'
    chat_id = Column(String(36), ForeignKey('chat.chat_id'), primary_key=True)
    title = Column(String(255), nullable=False)
    content_type = Column(String(50))
    file_path = Column(String(255))
    uploaded_at = Column(DateTime, default=func.now())
    chat = relationship("Chat", back_populates="syllabus")

class Textbook(Base):
    __tablename__ = 'textbook'
    chat_id = Column(String(36), ForeignKey('chat.chat_id'), primary_key=True)
    title = Column(String(255), nullable=False)
    content_type = Column(String(50))
    file_path = Column(String(255))
    uploaded_at = Column(DateTime, default=func.now())
    chat = relationship("Chat", back_populates="textbook")

class ChatMessage(Base):
    __tablename__ = 'chat_messages'
    message_id = Column(String(36), primary_key=True, default=generate_uuid)
    chat_id = Column(String(36), ForeignKey('chat.chat_id'))
    content = Column(Text, nullable=False)
    is_user = Column(Boolean, nullable=False)
    timestamp = Column(DateTime, default=func.now())
    chat = relationship("Chat", back_populates="messages")

class Summary(Base):
    __tablename__ = 'summaries'
    summary_id = Column(String(36), primary_key=True, default=generate_uuid)
    chat_id = Column(String(36), ForeignKey('chat.chat_id'))
    content = Column(Text)
    generated_at = Column(DateTime, default=func.now())
    chat = relationship("Chat", back_populates="summaries")

class MCQ(Base):
    __tablename__ = 'mcqs'
    mcq_id = Column(String(36), primary_key=True, default=generate_uuid)
    chat_id = Column(String(36), ForeignKey('chat.chat_id'))
    question = Column(Text, nullable=False)
    correct_answer = Column(Text, nullable=False)
    option_1 = Column(Text, nullable=False)
    option_2 = Column(Text, nullable=False)
    option_3 = Column(Text, nullable=False)
    chat = relationship("Chat", back_populates="mcqs")

class Diagram(Base):
    __tablename__ = 'diagrams'
    diagram_id = Column(String(36), primary_key=True, default=generate_uuid)
    chat_id = Column(String(36), ForeignKey('chat.chat_id'))
    title = Column(String(255))
    svg_content = Column(Text)
    generated_at = Column(DateTime, default=func.now())
    chat = relationship("Chat", back_populates="diagrams")

# Database configuration and initialization
DATABASE_URL = "postgresql://username:password@localhost:5432/rune_db"

def init_db():
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(engine)
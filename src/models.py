from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Enum
from sqlalchemy.orm import relationship
import enum
from src.database import Base
import uuid
from datetime import datetime

class FileTypeEnum(enum.Enum):
    syllabus = "syllabus"
    notes = "notes"

class FileStatusEnum(enum.Enum):
    pending = "pending"
    processed = "processed"

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    user_id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String)  # Added name field
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    chats = relationship("Chat", back_populates="user")

class Chat(Base):
    __tablename__ = "chats"

    chat_id = Column(String, primary_key=True, default=generate_uuid)
    title = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    user_id = Column(String, ForeignKey("users.user_id"))
    bookmarked = Column(Boolean, default=False)

    user = relationship("User", back_populates="chats")
    messages = relationship("ChatMessage", back_populates="chat")
    files = relationship("File", back_populates="chat")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    message_id = Column(String, primary_key=True, default=generate_uuid)
    chat_id = Column(String, ForeignKey("chats.chat_id"))
    content = Column(String)
    is_bot = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    chat = relationship("Chat", back_populates="messages") 

class File(Base):
    __tablename__ = "files"

    file_id = Column(String, primary_key=True, default=generate_uuid)
    chat_id = Column(String, ForeignKey("chats.chat_id"))
    file_name = Column(String, nullable=False)
    processed_at = Column(DateTime, nullable=True)
    file_type = Column(Enum(FileTypeEnum), nullable=False)
    status = Column(Enum(FileStatusEnum), default=FileStatusEnum.pending)
    content = Column(String, nullable=True)


    chat = relationship("Chat", back_populates="files")
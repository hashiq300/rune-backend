from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    user_id: str
    created_at: datetime
    last_login: Optional[datetime]

    class Config:
        orm_mode = True

class ChatBase(BaseModel):
    title: str

class ChatCreate(ChatBase):
    pass

class ChatResponse(ChatBase):
    chat_id: str
    user_id: str
    created_at: datetime

    class Config:
        orm_mode = True

class FileUploadBase(BaseModel):
    title: str
    content_type: str

class FileResponse(FileUploadBase):
    chat_id: str
    file_path: str
    uploaded_at: datetime

    class Config:
        orm_mode = True

class MessageBase(BaseModel):
    content: str
    is_user: bool

class MessageCreate(MessageBase):
    pass

class MessageResponse(MessageBase):
    message_id: str
    chat_id: str
    timestamp: datetime

    class Config:
        orm_mode = True

class MCQBase(BaseModel):
    question: str
    correct_answer: str
    option_1: str
    option_2: str
    option_3: str

class MCQResponse(MCQBase):
    mcq_id: str
    chat_id: str

    class Config:
        orm_mode = True

class DiagramBase(BaseModel):
    title: str
    svg_content: str

class DiagramResponse(DiagramBase):
    diagram_id: str
    chat_id: str
    generated_at: datetime

    class Config:
        orm_mode = True
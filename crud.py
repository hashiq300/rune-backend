from sqlalchemy.orm import Session
from . import models, schemas
from datetime import datetime

class CRUDBase:
    def __init__(self, model):
        self.model = model

    def get(self, db: Session, id: str):
        return db.query(self.model).filter(self.model.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        return db.query(self.model).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in):
        db_obj = self.model(**obj_in.dict())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: str):
        obj = db.query(self.model).get(id)
        db.delete(obj)
        db.commit()
        return obj

class CRUDUser(CRUDBase):
    def create(self, db: Session, obj_in: schemas.UserCreate):
        db_obj = models.User(
            name=obj_in.name,  # Added name field
            email=obj_in.email,
            password_hash=obj_in.password  # In practice, hash the password
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update_last_login(self, db: Session, user_id: str):
        db_obj = db.query(models.User).filter(models.User.user_id == user_id).first()
        db_obj.last_login = datetime.now()
        db.commit()
        db.refresh(db_obj)
        return db_obj

class CRUDChat(CRUDBase):
    def get_user_chats(self, db: Session, user_id: str):
        return db.query(models.Chat).filter(models.Chat.user_id == user_id).all()

    def create_with_files(self, db: Session, chat_in: schemas.ChatCreate, 
                        syllabus_in: schemas.FileUploadBase, 
                        textbook_in: schemas.FileUploadBase,
                        user_id: str):
        db_chat = models.Chat(**chat_in.dict(), user_id=user_id)
        db.add(db_chat)
        db.flush()

        db_syllabus = models.Syllabus(**syllabus_in.dict(), chat_id=db_chat.chat_id)
        db_textbook = models.Textbook(**textbook_in.dict(), chat_id=db_chat.chat_id)
        
        db.add(db_syllabus)
        db.add(db_textbook)
        db.commit()
        db.refresh(db_chat)
        return db_chat

class CRUDMessage(CRUDBase):
    def get_chat_messages(self, db: Session, chat_id: str):
        return db.query(models.ChatMessage) \
            .filter(models.ChatMessage.chat_id == chat_id) \
            .order_by(models.ChatMessage.timestamp.asc()) \
            .all()

user = CRUDUser(models.User)
chat = CRUDChat(models.Chat)
message = CRUDMessage(models.ChatMessage)
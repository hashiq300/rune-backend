import os

class Config:
    CHROMA_DIR = "chroma_db"
    EMBEDDING_MODEL = "qwen:1.8b"
    LLM_MODEL = "qwen:1.8b"
    ALLOWED_EXTENSIONS = {'txt', 'pdf'}
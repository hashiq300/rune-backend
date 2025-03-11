class Config:
    CHROMA_DIR = "chroma_db"
    EMBEDDING_MODEL = "nomic-embed-text:latest"
    LLM_MODEL = "qwen:1.8b"
    ALLOWED_EXTENSIONS = {'txt', 'pdf'}
    UPLOAD_FOLDER = "knowledge_base"
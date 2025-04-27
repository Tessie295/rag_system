import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    """Application settings."""
    APP_NAME: str = "Shakers AI Support System"
    API_PREFIX: str = "/api"
    DEBUG: bool = bool(os.getenv("DEBUG", "False") == "True")
    
    # LLM settings
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # Vector DB settings
    VECTOR_DB_PATH: str = os.getenv("VECTOR_DB_PATH", "./vectordb")
    
    # Knowledge base settings
    KNOWLEDGE_BASE_DIR: str = os.getenv("KNOWLEDGE_BASE_DIR", "./app/data/knowledge_base")
    
    # RAG settings
    MAX_SOURCES: int = int(os.getenv("MAX_SOURCES", "3"))
    SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.5"))
    
    # Recommendation settings
    MAX_RECOMMENDATIONS: int = int(os.getenv("MAX_RECOMMENDATIONS", "3"))
    
    class Config:
        env_file = ".env"

settings = Settings()
import os
from pydantic_settings import BaseSettings
from typing import List, Dict, Any


class Settings(BaseSettings):
    """Application configuration settings with performance optimizations."""

    # Basic application settings
    APP_NAME: str = "Shakers AI Support System"
    API_PREFIX: str = "/api"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
    PORT: int = int(os.getenv("PORT", "8000"))

    # Directory paths
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_DIR: str = os.path.join(BASE_DIR, "app/data")
    KNOWLEDGE_BASE_DIR: str = os.path.join(DATA_DIR, "knowledge_base")
    VECTOR_DB_PATH: str = os.path.join(DATA_DIR, "vector_db")

    # LLM settings - Optimized for speed
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    LLM_MODEL: str = os.getenv(
        "LLM_MODEL", "gpt-3.5-turbo"
    )  # Use a faster model gpt-3.5-turbo-0125?
    EVALUATION_MODEL: str = os.getenv("EVALUATION_MODEL", "gpt-3.5-turbo")
    USE_LLM_FOR_EVALUATION: bool = os.getenv(
        "USE_LLM_FOR_EVALUATION", "False"
    ).lower() in (
        "true",
        "1",
        "t",
    )  # Disable by default for speed

    # Timeouts for external API calls
    LLM_TIMEOUT: int = 3  # 3 seconds timeout for LLM calls
    EMBEDDINGS_TIMEOUT: int = 2  # 2 seconds timeout for embedding calls

    # RAG settings
    MAX_SOURCES: int = 5
    SIMILARITY_THRESHOLD: float = 0.15  # Slightly lower threshold for faster filtering
    AMBIGUITY_THRESHOLD: float = 0.15
    CHUNK_SIZE: int = 1200
    CHUNK_OVERLAP: int = 300

    # Recommendation settings
    MAX_RECOMMENDATIONS: int = 3
    DIVERSITY_WEIGHT: float = 0.3

    # Performance settings
    MAX_RESPONSE_TIME: float = 5.0  # Target maximum response time in seconds
    ENABLE_RESPONSE_TIMEOUT: bool = True  # Enable timeout for responses
    RESPONSE_TIMEOUT: float = 7  # Cut off processing after this time

    # Caching settings - Added for performance
    ENABLE_CACHING: bool = True  # Enable response caching
    CACHE_TTL: int = 3600  # Cache TTL in seconds (1 hour)
    MAX_CACHE_ITEMS: int = 1000  # Maximum number of cached items

    # Update intervals
    KB_UPDATE_INTERVAL: int = 3600  # Check for knowledge base updates every hour
    METRICS_BACKUP_INTERVAL: int = 1800  # Backup metrics every 30 minutes

    # Feature flags
    ENABLE_EVALUATION: bool = False  # Disable by default for speed
    ENABLE_PARALLEL_PROCESSING: bool = True  # Enable parallel processing
    MAX_WORKERS: int = 4  # Maximum worker threads

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Create settings instance
settings = Settings()

# Ensure required directories exist
os.makedirs(settings.DATA_DIR, exist_ok=True)
os.makedirs(settings.KNOWLEDGE_BASE_DIR, exist_ok=True)

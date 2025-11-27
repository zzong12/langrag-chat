"""Configuration management for the RAG application."""
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""
    
    # LLM Configuration
    LLM_API_BASE_URL: str = os.getenv("LLM_API_BASE_URL", "https://api.openai.com/v1")
    LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "gpt-3.5-turbo")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    
    # Pinecone Configuration
    PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "")
    PINECONE_HOST: str = os.getenv("PINECONE_HOST", "")
    PINECONE_ENVIRONMENT: str = os.getenv("PINECONE_ENVIRONMENT", "us-east-1")
    PINECONE_INDEX_NAME: str = os.getenv("PINECONE_INDEX_NAME", "rag-index")
    
    # Embedding Configuration
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002")
    
    # Application Configuration
    UPLOAD_DIR: Path = Path(os.getenv("UPLOAD_DIR", "./uploads"))
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "104857600"))  # 100MB default
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "1000"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "200"))
    
    # RAG Configuration
    TOP_K_RESULTS: int = int(os.getenv("TOP_K_RESULTS", "4"))
    
    # Server Configuration
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    def __init__(self):
        """Initialize settings and create necessary directories."""
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    
    def validate(self) -> tuple[bool, Optional[str]]:
        """Validate that required settings are present."""
        if not self.LLM_API_KEY:
            return False, "LLM_API_KEY is required"
        if not self.PINECONE_API_KEY:
            return False, "PINECONE_API_KEY is required"
        return True, None


# Global settings instance
settings = Settings()


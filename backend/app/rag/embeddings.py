"""Embedding model setup for document and query embeddings."""
from langchain_openai import OpenAIEmbeddings
from app.config import settings


def get_embeddings() -> OpenAIEmbeddings:
    """Initialize and return OpenAI-compatible embeddings model."""
    return OpenAIEmbeddings(
        model=settings.EMBEDDING_MODEL,
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_API_BASE_URL,
    )


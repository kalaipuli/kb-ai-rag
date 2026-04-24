"""Application configuration loaded from environment variables via pydantic-settings."""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime configuration for the kb-ai-rag backend.

    Values are read from environment variables (case-insensitive) or a .env file
    located in the working directory.  See backend/.env.example for the full list.
    """

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    # Azure OpenAI / AI Foundry
    azure_openai_endpoint: str
    azure_openai_api_key: SecretStr
    azure_openai_api_version: str = "2024-08-01-preview"
    azure_chat_deployment: str = "gpt-4o"
    azure_embedding_deployment: str = "text-embedding-3-large"

    # Qdrant vector store
    qdrant_url: str = "http://qdrant:6333"
    qdrant_collection: str = "kb_documents"

    # Service authentication
    api_key: SecretStr

    # Document ingestion
    data_dir: str = "/app/data"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    embedding_vector_size: int = 3072
    embedding_batch_size: int = 100
    bm25_index_path: str = "/app/data/bm25_index.pkl"

    # LangSmith tracing (optional; leave blank to disable)
    langsmith_api_key: str = ""
    langchain_tracing_v2: bool = False

    # Tavily web-search fallback (Phase 2+; leave blank until then)
    tavily_api_key: str = ""


@lru_cache
def get_settings() -> Settings:
    """Return the cached application Settings instance.

    The result is cached after the first call so that the same object is
    returned on every subsequent call within a process.  Call
    ``get_settings.cache_clear()`` in tests to force re-instantiation.
    """
    return Settings()  # type: ignore[call-arg]

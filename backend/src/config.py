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
    azure_embedding_deployment: str = "text-embedding-ada-002"

    # Qdrant vector store
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "kb_documents"

    # Service authentication
    api_key: SecretStr
    cors_origins: list[str] = []

    # Document ingestion
    data_dir: str = "data"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    embedding_vector_size: int = 1536
    embedding_batch_size: int = 100
    embedding_max_concurrency: int = 3
    # Seconds to sleep inside the semaphore after each batch completes.
    # Keeps per-slot throughput bounded so TPM/RPM limits are not exceeded.
    embedding_inter_batch_delay: float = 1.0
    bm25_index_path: str = "data/bm25_index.pkl"

    # Hybrid retrieval
    retrieval_top_k: int = 10
    reranker_top_k: int = 5
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    rrf_k: int = 60

    # LangSmith tracing (optional; leave blank to disable)
    langsmith_api_key: SecretStr = SecretStr("")
    langchain_tracing_v2: bool = False

    # Tavily web-search fallback (Phase 2+; leave blank until then)
    tavily_api_key: SecretStr = SecretStr("")

    # Chunking strategy
    chunk_strategy: str = "recursive_character"
    chunk_tokenizer_model: str = "cl100k_base"

    # Evaluation baseline
    eval_baseline_path: str = "data/eval_baseline.json"

    # LangGraph SqliteSaver checkpointer (Phase 2+; single-worker only — see ADR-004)
    sqlite_checkpointer_path: str = "data/checkpointer.sqlite"
    sqlite_checkpointer_ttl_days: int = 7

    # Graph node tuning
    grader_batch_size: int = 10
    grader_threshold: float = 0.5
    critic_threshold: float = 0.7
    graph_max_retries: int = 2


@lru_cache
def get_settings() -> Settings:
    """Return the cached application Settings instance.

    The result is cached after the first call so that the same object is
    returned on every subsequent call within a process.  Call
    ``get_settings.cache_clear()`` in tests to force re-instantiation.
    """
    return Settings()  # type: ignore[call-arg]

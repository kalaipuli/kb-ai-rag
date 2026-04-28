"""Domain-specific exceptions for the kb-ai-rag backend.

All exceptions inherit from KBRagError so callers can catch the base class
when they need a broad handler, or catch a specific subclass for targeted
error recovery.
"""


class KBRagError(Exception):
    """Base exception for all kb-ai-rag domain errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class IngestionError(KBRagError):
    """Raised when document loading, chunking, or upsert fails during ingestion."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class RetrievalError(KBRagError):
    """Raised when vector search, BM25 search, or RRF fusion fails."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class EmbeddingError(KBRagError):
    """Raised when an Azure OpenAI embedding request fails or returns unexpected data."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class ConfigurationError(KBRagError):
    """Raised when required configuration is missing or carries an invalid value."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class GenerationError(KBRagError):
    """Raised when the LLM generation step fails or returns an unexpected result."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class GraderError(KBRagError):
    """Raised when the grader LLM batch call fails for all chunks in a node invocation."""

    def __init__(self, message: str) -> None:
        super().__init__(message)

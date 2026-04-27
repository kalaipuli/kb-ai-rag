"""FastAPI application entry point for kb-ai-rag backend.

The lifespan handler wires up structured logging and emits a startup event.
Middleware and exception handlers are registered here; route logic lives in the
individual route modules under ``src/api/routes/``.
"""

import json
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from qdrant_client import AsyncQdrantClient

from src.api.middleware.auth import api_key_middleware
from src.api.routes.collections import router as collections_router
from src.api.routes.eval import router as eval_router
from src.api.routes.health import router as health_router
from src.api.routes.ingest import router as ingest_router
from src.api.routes.query import router as query_router
from src.api.routes.query_agentic import router as query_agentic_router
from src.api.schemas import ErrorResponse
from src.config import get_settings
from src.exceptions import (
    ConfigurationError,
    EmbeddingError,
    IngestionError,
    KBRagError,
    RetrievalError,
)
from src.generation.chain import GenerationChain
from src.graph.builder import build_graph
from src.ingestion.bm25_store import BM25Store
from src.ingestion.embedder import Embedder
from src.logging_config import configure_logging
from src.retrieval.retriever import HybridRetriever

logger = structlog.get_logger(__name__)

# Single call site — consumed by CORSMiddleware below and reused in lifespan
# so that env-var overrides applied before import (e.g. in tests) are
# reflected consistently rather than potentially reading two different states.
_settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize singleton services and expose via app.state."""
    configure_logging()
    settings = _settings

    bm25_store = BM25Store(index_path=Path(settings.bm25_index_path))
    if Path(settings.bm25_index_path).exists():
        bm25_store.load()

    embedder = Embedder(settings=settings)
    app.state.embedder = embedder
    retriever = HybridRetriever(settings=settings, bm25_store=bm25_store, embedder=embedder)
    app.state.compiled_graph = await build_graph(settings=settings, retriever=retriever)
    app.state.generation_chain = GenerationChain(settings=settings, hybrid_retriever=retriever)
    app.state.bm25_store = bm25_store
    app.state.qdrant_client = AsyncQdrantClient(url=settings.qdrant_url)

    logger.info("startup", service="kb-ai-rag-backend")
    yield

    await retriever.close()
    await app.state.qdrant_client.close()
    logger.info("shutdown", service="kb-ai-rag-backend")


app = FastAPI(
    title="KB AI RAG API",
    description="Enterprise Agentic RAG platform — knowledge-base query and ingestion API.",
    version="0.1.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.middleware("http")(api_key_middleware)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(health_router, prefix="/api/v1")
app.include_router(ingest_router, prefix="/api/v1")
app.include_router(query_router, prefix="/api/v1")
app.include_router(query_agentic_router, prefix="/api/v1", tags=["query"])
app.include_router(collections_router, prefix="/api/v1")
app.include_router(eval_router, prefix="/api/v1")

# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------
# More specific subclass handlers must be registered before the base-class
# handler so FastAPI matches the most specific type first.


@app.exception_handler(ConfigurationError)
async def configuration_error_handler(request: Request, exc: ConfigurationError) -> JSONResponse:
    """Translate ConfigurationError to HTTP 422."""
    logger.error("configuration_error", detail=exc.message, path=request.url.path)
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(detail=exc.message).model_dump(),
    )


@app.exception_handler(IngestionError)
async def ingestion_error_handler(request: Request, exc: IngestionError) -> JSONResponse:
    """Translate IngestionError to HTTP 422."""
    logger.error("ingestion_error", detail=exc.message, path=request.url.path)
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(detail=exc.message).model_dump(),
    )


@app.exception_handler(RetrievalError)
async def retrieval_error_handler(request: Request, exc: RetrievalError) -> JSONResponse:
    """Translate RetrievalError to HTTP 503."""
    logger.error("retrieval_error", detail=exc.message, path=request.url.path)
    return JSONResponse(
        status_code=503,
        content=ErrorResponse(detail=exc.message).model_dump(),
    )


@app.exception_handler(EmbeddingError)
async def embedding_error_handler(request: Request, exc: EmbeddingError) -> JSONResponse:
    """Translate EmbeddingError to HTTP 503."""
    logger.error("embedding_error", detail=exc.message, path=request.url.path)
    return JSONResponse(
        status_code=503,
        content=ErrorResponse(detail=exc.message).model_dump(),
    )


@app.exception_handler(KBRagError)
async def kb_rag_error_handler(request: Request, exc: KBRagError) -> JSONResponse:
    """Translate any unhandled KBRagError subclass to HTTP 500."""
    logger.error(
        "unexpected_kb_error",
        error_type=type(exc).__name__,
        detail=exc.message,
        path=request.url.path,
    )
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(detail=exc.message).model_dump(),
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Translate Pydantic request-validation errors to HTTP 422.

    ``exc.errors()`` is a list of dicts; we serialise it to a JSON string so
    that the wire format matches ``ApiError { detail: string }`` on the
    frontend.
    """
    detail = json.dumps(exc.errors(), default=str)
    logger.warning(
        "request_validation_error",
        path=request.url.path,
        detail=detail,
    )
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(detail=detail).model_dump(),
    )

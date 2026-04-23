"""FastAPI application entry point for kb-ai-rag backend.

The lifespan handler wires up structured logging and emits a startup event.
Middleware and exception handlers are registered here; route logic lives in the
individual route modules under ``src/api/routes/``.
"""

import json
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.middleware.auth import api_key_middleware
from src.api.routes.health import router as health_router
from src.api.schemas import ErrorResponse
from src.exceptions import (
    ConfigurationError,
    EmbeddingError,
    IngestionError,
    KBRagError,
    RetrievalError,
)
from src.logging_config import configure_logging

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Configure logging and emit a startup event, then run the application."""
    configure_logging()
    logger.info("startup", service="kb-ai-rag-backend")
    yield
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
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.middleware("http")(api_key_middleware)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(health_router, prefix="/api/v1")

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

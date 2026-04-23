"""API-key authentication middleware.

Requests to protected paths must carry an ``X-API-Key`` header whose value
matches ``settings.api_key``.  Paths listed in ``EXEMPT_PATHS`` are always
allowed through without authentication.
"""

from collections.abc import Awaitable, Callable

import structlog
from fastapi import Request, Response
from fastapi.responses import JSONResponse

from src.config import get_settings

logger = structlog.get_logger(__name__)

# Paths that bypass API-key authentication.
EXEMPT_PATHS: frozenset[str] = frozenset(
    {
        "/api/v1/health",
        "/docs",
        "/openapi.json",
        "/redoc",
    }
)


async def api_key_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Validate the X-API-Key header on every non-exempt request.

    Args:
        request: The incoming HTTP request.
        call_next: ASGI callable that passes the request to the next layer.

    Returns:
        A 401 JSONResponse when the key is absent or invalid, otherwise the
        response produced by the downstream handler.
    """
    if request.url.path in EXEMPT_PATHS:
        return await call_next(request)

    settings = get_settings()
    api_key = request.headers.get("X-API-Key", "")
    if not api_key or api_key != settings.api_key:
        logger.warning("auth_failed", path=request.url.path)
        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid or missing API key"},
        )

    return await call_next(request)

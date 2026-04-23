"""Structured logging configuration using structlog.

Call ``configure_logging()`` once at application startup (inside the FastAPI
lifespan handler) before any module emits log events.
"""

import logging

import structlog


def configure_logging() -> None:
    """Configure structlog with a JSON processor chain.

    The chain applied to every log event (in order):
    1. add_log_level        — adds ``level`` key
    2. add_logger_name      — adds ``logger`` key (module __name__)
    3. TimeStamper          — adds ISO-8601 ``timestamp`` key
    4. StackInfoRenderer    — renders stack info when present
    5. format_exc_info      — renders exc_info tracebacks as strings
    6. JSONRenderer         — serialises the final event dict to JSON

    ``structlog.stdlib.LoggerFactory`` is used so that ``add_logger_name``
    can read the ``.name`` attribute from the underlying stdlib Logger.
    Third-party libraries (uvicorn, httpx, etc.) are routed through stdlib
    logging so they also produce structured output.
    """
    logging.basicConfig(
        format="%(message)s",
        level=logging.INFO,
    )

    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=False,
    )

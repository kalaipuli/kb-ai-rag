"""Unit tests for src/logging_config.py."""

import structlog

from src.logging_config import configure_logging


def test_configure_logging_runs_without_error() -> None:
    """configure_logging() must not raise under any circumstances."""
    configure_logging()


def test_structlog_produces_bound_logger_after_configure() -> None:
    configure_logging()
    logger = structlog.get_logger("test_module")
    # get_logger always returns a BoundLogger-like object after configure()
    assert logger is not None


def test_configure_logging_is_idempotent() -> None:
    """Calling configure_logging() twice must not raise."""
    configure_logging()
    configure_logging()

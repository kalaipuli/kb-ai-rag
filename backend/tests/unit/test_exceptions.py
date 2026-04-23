"""Unit tests for src/exceptions.py."""

import pytest

from src.exceptions import (
    ConfigurationError,
    EmbeddingError,
    IngestionError,
    KBRagError,
    RetrievalError,
)


def test_kbrag_error_is_exception() -> None:
    err = KBRagError("base error")
    assert isinstance(err, Exception)
    assert err.message == "base error"
    assert str(err) == "base error"


def test_ingestion_error_inherits_from_kbrag_error() -> None:
    err = IngestionError("load failed")
    assert isinstance(err, KBRagError)
    assert err.message == "load failed"


def test_retrieval_error_inherits_from_kbrag_error() -> None:
    err = RetrievalError("search failed")
    assert isinstance(err, KBRagError)
    assert err.message == "search failed"


def test_embedding_error_inherits_from_kbrag_error() -> None:
    err = EmbeddingError("azure call failed")
    assert isinstance(err, KBRagError)
    assert err.message == "azure call failed"


def test_configuration_error_inherits_from_kbrag_error() -> None:
    err = ConfigurationError("missing key")
    assert isinstance(err, KBRagError)
    assert err.message == "missing key"


def test_can_catch_specific_subclass() -> None:
    with pytest.raises(IngestionError, match="load failed"):
        raise IngestionError("load failed")


def test_can_catch_via_base_class() -> None:
    with pytest.raises(KBRagError):
        raise RetrievalError("qdrant down")

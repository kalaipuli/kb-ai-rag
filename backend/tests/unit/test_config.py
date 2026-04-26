"""Unit tests for src/config.py."""

import pytest
from pydantic import ValidationError

from src.config import Settings, get_settings


def _minimal_settings(**overrides: object) -> Settings:
    """Return a Settings with all required fields populated.

    ``_env_file=None`` prevents pydantic-settings from reading the local .env
    so unit tests exercise the Python-level defaults, not deployment values.
    """
    defaults: dict[str, object] = {
        "_env_file": None,
        "azure_openai_endpoint": "https://example.openai.azure.com/",
        "azure_openai_api_key": "sk-test",
        "api_key": "my-api-key",
    }
    defaults.update(overrides)
    return Settings(**defaults)  # type: ignore[arg-type]


def test_required_fields_accepted() -> None:
    s = _minimal_settings()
    assert s.azure_openai_endpoint == "https://example.openai.azure.com/"
    assert s.azure_openai_api_key.get_secret_value() == "sk-test"
    assert s.api_key.get_secret_value() == "my-api-key"


def test_default_values() -> None:
    s = _minimal_settings()
    assert s.azure_openai_api_version == "2024-08-01-preview"
    assert s.azure_chat_deployment == "gpt-4o"
    assert s.azure_embedding_deployment == "text-embedding-ada-002"
    assert s.qdrant_url == "http://localhost:6333"
    assert s.qdrant_collection == "kb_documents"
    assert s.data_dir == "data"
    assert s.chunk_size == 1000
    assert s.chunk_overlap == 200
    assert s.langsmith_api_key == ""
    assert s.langchain_tracing_v2 is False
    assert s.tavily_api_key == ""


def test_overrides_applied() -> None:
    s = _minimal_settings(
        qdrant_url="http://custom-qdrant:6333",
        chunk_size=512,
        langchain_tracing_v2=True,
    )
    assert s.qdrant_url == "http://custom-qdrant:6333"
    assert s.chunk_size == 512
    assert s.langchain_tracing_v2 is True


def test_get_settings_returns_settings_instance() -> None:
    """get_settings() must return a valid Settings object and cache it."""
    get_settings.cache_clear()
    s1 = get_settings()
    s2 = get_settings()
    assert isinstance(s1, Settings)
    assert s1 is s2  # same cached object
    get_settings.cache_clear()


def test_cors_origins_default_is_wildcard() -> None:
    s = _minimal_settings()
    assert s.cors_origins == ["*"]


def test_missing_required_field_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Settings must raise ValidationError when required env vars are absent.

    ``_env_file=None`` isolates the test from the local .env file so that only
    the explicitly supplied kwargs are considered — env var presence in the
    process environment is also cleared via monkeypatch.
    """
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
    monkeypatch.delenv("API_KEY", raising=False)
    # Only azure_openai_api_key is supplied — endpoint and api_key are missing.
    with pytest.raises(ValidationError):
        Settings(_env_file=None, azure_openai_api_key="k")  # type: ignore[call-arg]

"""Unit tests for SplitterFactory and ChunkStrategy."""

import pytest
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.config import Settings
from src.exceptions import ConfigurationError
from src.ingestion.splitter_factory import ChunkStrategy, SplitterFactory


def _make_settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "azure_openai_endpoint": "https://test.openai.azure.com/",
        "azure_openai_api_key": "key",
        "api_key": "apikey",
        "chunk_size": 500,
        "chunk_overlap": 50,
        "chunk_strategy": "recursive_character",
        "chunk_tokenizer_model": "cl100k_base",
        "eval_baseline_path": "data/eval_baseline.json",
    }
    defaults.update(overrides)
    return Settings(**defaults)  # type: ignore[arg-type]


class TestChunkStrategyEnum:
    def test_all_strategy_values(self) -> None:
        assert ChunkStrategy.recursive_character.value == "recursive_character"
        assert ChunkStrategy.sentence_window.value == "sentence_window"
        assert ChunkStrategy.semantic.value == "semantic"

    def test_is_str_enum(self) -> None:
        assert isinstance(ChunkStrategy.recursive_character, str)


class TestSplitterFactoryRecursiveCharacter:
    def test_returns_recursive_character_splitter(self) -> None:
        settings = _make_settings(chunk_strategy="recursive_character")
        splitter = SplitterFactory.build(settings)
        assert isinstance(splitter, RecursiveCharacterTextSplitter)

    def test_splitter_has_split_text_method(self) -> None:
        settings = _make_settings(chunk_strategy="recursive_character")
        splitter = SplitterFactory.build(settings)
        assert callable(getattr(splitter, "split_text", None))

    def test_recursive_splitter_produces_output(self) -> None:
        settings = _make_settings(chunk_strategy="recursive_character", chunk_size=100, chunk_overlap=10)
        splitter = SplitterFactory.build(settings)
        text = "word " * 200
        chunks = splitter.split_text(text)
        assert len(chunks) >= 2


class TestSplitterFactorySentenceWindow:
    def test_returns_splitter_with_split_text(self) -> None:
        from src.ingestion.sentence_window_splitter import SentenceWindowSplitter

        settings = _make_settings(chunk_strategy="sentence_window")
        splitter = SplitterFactory.build(settings)
        assert isinstance(splitter, SentenceWindowSplitter)
        assert callable(getattr(splitter, "split_text", None))

    def test_sentence_window_produces_output(self) -> None:
        settings = _make_settings(chunk_strategy="sentence_window", chunk_size=100, chunk_overlap=10)
        splitter = SplitterFactory.build(settings)
        text = (
            "The quick brown fox jumps over the lazy dog. " * 10
            + "Pack my box with five dozen liquor jugs. " * 10
        )
        chunks = splitter.split_text(text)
        assert len(chunks) >= 1


class TestSplitterFactorySemantic:
    def test_semantic_raises_configuration_error(self) -> None:
        settings = _make_settings(chunk_strategy="semantic")
        with pytest.raises(ConfigurationError) as exc_info:
            SplitterFactory.build(settings)
        assert "langchain-experimental" in str(exc_info.value)
        assert "ADR-009" in str(exc_info.value)

    def test_semantic_with_embedder_still_raises(self) -> None:
        """Passing an embedder does not bypass the deferred strategy guard."""
        settings = _make_settings(chunk_strategy="semantic")
        with pytest.raises(ConfigurationError) as exc_info:
            SplitterFactory.build(settings, embedder=object())
        assert "langchain-experimental" in str(exc_info.value)


class TestSplitterFactoryUnknownStrategy:
    def test_unknown_strategy_raises_configuration_error(self) -> None:
        settings = _make_settings(chunk_strategy="nonexistent_strategy")
        with pytest.raises(ConfigurationError) as exc_info:
            SplitterFactory.build(settings)
        assert "nonexistent_strategy" in str(exc_info.value)
        assert "Valid values" in str(exc_info.value)

    def test_error_message_lists_valid_values(self) -> None:
        settings = _make_settings(chunk_strategy="bad_value")
        with pytest.raises(ConfigurationError) as exc_info:
            SplitterFactory.build(settings)
        msg = str(exc_info.value)
        for strategy in ChunkStrategy:
            assert strategy.value in msg

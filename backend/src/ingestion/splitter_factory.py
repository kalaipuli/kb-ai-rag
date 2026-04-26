"""Factory for creating text splitter instances based on ChunkStrategy."""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum

import tiktoken
from langchain_text_splitters import RecursiveCharacterTextSplitter, TextSplitter

from src.config import Settings
from src.exceptions import ConfigurationError

_SPLITTER_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]


class ChunkStrategy(str, Enum):
    """Supported chunking strategies."""

    recursive_character = "recursive_character"
    sentence_window = "sentence_window"
    semantic = "semantic"


class SplitterFactory:
    """Build a ``TextSplitter`` for the strategy configured in ``Settings``."""

    @staticmethod
    def build(settings: Settings, embedder: object | None = None) -> TextSplitter:
        """Return a TextSplitter for the configured strategy.

        Parameters
        ----------
        settings:
            Application settings; ``chunk_strategy``, ``chunk_size``,
            ``chunk_overlap``, and ``chunk_tokenizer_model`` are read here.
        embedder:
            Reserved for future semantic strategy use.  Currently unused.

        Raises
        ------
        ConfigurationError
            When the strategy name is unknown or the strategy is unavailable
            (semantic strategy deferred pending langchain-experimental >=1.0).
        """
        try:
            strategy = ChunkStrategy(settings.chunk_strategy)
        except ValueError as exc:
            raise ConfigurationError(
                f"Unknown chunk strategy: '{settings.chunk_strategy}'. "
                f"Valid values: {[s.value for s in ChunkStrategy]}"
            ) from exc

        enc = tiktoken.get_encoding(settings.chunk_tokenizer_model)
        length_fn: Callable[[str], int] = lambda text: len(enc.encode(text))  # noqa: E731

        if strategy == ChunkStrategy.recursive_character:
            return RecursiveCharacterTextSplitter(
                chunk_size=settings.chunk_size,
                chunk_overlap=settings.chunk_overlap,
                separators=_SPLITTER_SEPARATORS,
                length_function=length_fn,
            )

        if strategy == ChunkStrategy.sentence_window:
            from src.ingestion.sentence_window_splitter import SentenceWindowSplitter

            return SentenceWindowSplitter(
                chunk_size=settings.chunk_size,
                chunk_overlap=settings.chunk_overlap,
                length_function=length_fn,
            )

        if strategy == ChunkStrategy.semantic:
            raise ConfigurationError(
                "semantic strategy requires langchain-experimental; see ADR-009"
            )

        # Should never reach here — enum exhaustion ensures all cases above are covered.
        raise ConfigurationError(f"Unhandled strategy: {strategy}")  # pragma: no cover

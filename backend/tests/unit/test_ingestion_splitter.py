"""Unit tests for DocumentSplitter."""

import pytest

from src.config import Settings
from src.exceptions import ConfigurationError
from src.ingestion.models import Document
from src.ingestion.splitter import DocumentSplitter


def _make_settings(
    chunk_size: int = 200,
    chunk_overlap: int = 20,
    chunk_strategy: str = "recursive_character",
) -> Settings:
    return Settings(
        azure_openai_endpoint="https://test.openai.azure.com/",
        azure_openai_api_key="key",
        api_key="apikey",
        data_dir="/tmp/test-data",
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        embedding_batch_size=16,
        bm25_index_path="/tmp/bm25.pkl",
        chunk_strategy=chunk_strategy,
        chunk_tokenizer_model="cl100k_base",
        eval_baseline_path="data/eval_baseline.json",
    )


def _make_doc(content: str, doc_id: str = "doc-1", file_type: str = "txt") -> Document:
    return Document(
        content=content,
        metadata={
            "doc_id": doc_id,
            "source_path": f"/tmp/{doc_id}.txt",
            "filename": f"{doc_id}.txt",
            "file_type": file_type,
            "page_number": -1,
        },
    )


# ---------------------------------------------------------------------------
# Basic splitting
# ---------------------------------------------------------------------------


class TestDocumentSplitterBasic:
    def test_single_doc_produces_chunks(self) -> None:
        # Use varied word content so tiktoken produces realistic token counts.
        # 500 words at ~1 token each → ~500 tokens; chunk_size=200 → at least 2 chunks.
        words = ["the", "quick", "brown", "fox", "jumps", "over", "lazy", "dog"]
        content = " ".join(words * 70)  # ~560 tokens of real words
        doc = _make_doc(content)
        splitter = DocumentSplitter(_make_settings(chunk_size=200, chunk_overlap=20))
        chunks = splitter.split([doc])
        assert len(chunks) >= 2

    def test_chunk_index_is_sequential(self) -> None:
        content = ("word " * 60 + "\n\n") * 3
        doc = _make_doc(content)
        splitter = DocumentSplitter(_make_settings(chunk_size=150, chunk_overlap=10))
        chunks = splitter.split([doc])
        indices = [c.metadata["chunk_index"] for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_total_chunks_is_correct(self) -> None:
        content = ("word " * 60 + "\n\n") * 3
        doc = _make_doc(content)
        splitter = DocumentSplitter(_make_settings(chunk_size=150, chunk_overlap=10))
        chunks = splitter.split([doc])
        expected_total = len(chunks)
        for chunk in chunks:
            assert chunk.metadata["total_chunks"] == expected_total

    def test_char_count_matches_text_length(self) -> None:
        content = "Hello world. " * 20
        doc = _make_doc(content)
        splitter = DocumentSplitter(_make_settings(chunk_size=100, chunk_overlap=10))
        chunks = splitter.split([doc])
        for chunk in chunks:
            assert chunk.metadata["char_count"] == len(chunk.text)

    def test_doc_id_propagated(self) -> None:
        content = "Some content repeated many times. " * 15
        doc = _make_doc(content, doc_id="my-doc-id")
        splitter = DocumentSplitter(_make_settings(chunk_size=100, chunk_overlap=10))
        chunks = splitter.split([doc])
        for chunk in chunks:
            assert chunk.metadata["doc_id"] == "my-doc-id"

    def test_metadata_fields_all_present(self) -> None:
        content = "Content " * 30
        doc = _make_doc(content)
        splitter = DocumentSplitter(_make_settings(chunk_size=100, chunk_overlap=10))
        chunks = splitter.split([doc])
        required_fields = {
            "doc_id",
            "chunk_id",
            "source_path",
            "filename",
            "file_type",
            "title",
            "page_number",
            "chunk_index",
            "total_chunks",
            "char_count",
            "ingested_at",
            "tags",
        }
        for chunk in chunks:
            assert required_fields.issubset(chunk.metadata.keys())

    def test_chunk_ids_are_unique(self) -> None:
        content = "Unique chunk content. " * 40
        doc = _make_doc(content)
        splitter = DocumentSplitter(_make_settings(chunk_size=100, chunk_overlap=10))
        chunks = splitter.split([doc])
        ids = [c.metadata["chunk_id"] for c in chunks]
        assert len(ids) == len(set(ids))

    def test_title_max_80_chars(self) -> None:
        content = "A" * 200
        doc = _make_doc(content)
        splitter = DocumentSplitter(_make_settings(chunk_size=200, chunk_overlap=10))
        chunks = splitter.split([doc])
        for chunk in chunks:
            assert len(chunk.metadata["title"]) <= 80

    def test_tags_is_empty_list(self) -> None:
        content = "Some content here. " * 10
        doc = _make_doc(content)
        splitter = DocumentSplitter(_make_settings(chunk_size=100, chunk_overlap=10))
        chunks = splitter.split([doc])
        for chunk in chunks:
            assert chunk.metadata["tags"] == []

    def test_ingested_at_is_iso8601(self) -> None:
        import re

        content = "Temporal content. " * 10
        doc = _make_doc(content)
        splitter = DocumentSplitter(_make_settings(chunk_size=100, chunk_overlap=10))
        chunks = splitter.split([doc])
        iso_pattern = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
        for chunk in chunks:
            assert iso_pattern.match(chunk.metadata["ingested_at"])


# ---------------------------------------------------------------------------
# Short-chunk filtering
# ---------------------------------------------------------------------------


class TestShortChunkFiltering:
    def test_chunks_below_100_chars_discarded(self) -> None:
        # One big chunk + one tiny trailer
        content = "A" * 500 + "\n\nX"  # "X" alone is 1 char — must be discarded
        doc = _make_doc(content)
        splitter = DocumentSplitter(_make_settings(chunk_size=500, chunk_overlap=0))
        chunks = splitter.split([doc])
        for chunk in chunks:
            assert chunk.metadata["char_count"] >= 100

    def test_all_content_short_returns_empty(self) -> None:
        # Tiny content that will produce only sub-100-char chunks
        doc = _make_doc("Hi")
        splitter = DocumentSplitter(_make_settings(chunk_size=200, chunk_overlap=10))
        chunks = splitter.split([doc])
        assert chunks == []


# ---------------------------------------------------------------------------
# Multiple documents
# ---------------------------------------------------------------------------


class TestMultipleDocuments:
    def test_two_docs_independent_indices(self) -> None:
        content = "Long enough content for splitting purposes here. " * 10
        doc1 = _make_doc(content, doc_id="doc-A")
        doc2 = _make_doc(content, doc_id="doc-B")
        splitter = DocumentSplitter(_make_settings(chunk_size=120, chunk_overlap=10))
        chunks = splitter.split([doc1, doc2])

        doc_a_chunks = [c for c in chunks if c.metadata["doc_id"] == "doc-A"]
        doc_b_chunks = [c for c in chunks if c.metadata["doc_id"] == "doc-B"]

        # Each doc has 0-based sequential indices independently
        assert [c.metadata["chunk_index"] for c in doc_a_chunks] == list(range(len(doc_a_chunks)))
        assert [c.metadata["chunk_index"] for c in doc_b_chunks] == list(range(len(doc_b_chunks)))

    def test_empty_doc_list_returns_empty(self) -> None:
        splitter = DocumentSplitter(_make_settings())
        assert splitter.split([]) == []


# ---------------------------------------------------------------------------
# Token-aware chunk boundaries (T03)
# ---------------------------------------------------------------------------


class TestTokenAwareChunking:
    def test_chunk_token_count_does_not_exceed_chunk_size(self) -> None:
        """All chunks must have a token count <= chunk_size (plus overlap tolerance)."""
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        # Build content that is clearly larger than chunk_size=100 tokens.
        content = (
            ("The quick brown fox jumps over the lazy dog. " * 20)
            + "\n\n"
            + ("Pack my box with five dozen liquor jugs. " * 20)
        )
        doc = _make_doc(content)
        chunk_size = 100
        splitter = DocumentSplitter(_make_settings(chunk_size=chunk_size, chunk_overlap=10))
        chunks = splitter.split([doc])
        assert len(chunks) >= 2, "Content should produce multiple chunks"
        for chunk in chunks:
            token_count = len(enc.encode(chunk.text))
            # Allow a small margin because the splitter may include a partial
            # final token at a separator boundary.
            assert (
                token_count <= chunk_size + 20
            ), f"Chunk has {token_count} tokens, exceeds limit of {chunk_size + 20}"


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


class TestDocumentSplitterErrorPaths:
    def test_invalid_strategy_raises_configuration_error(self) -> None:
        """SplitterFactory.build() raises ConfigurationError for unknown strategies;
        DocumentSplitter must propagate it rather than swallow it."""
        settings = _make_settings(chunk_strategy="invalid_strategy")
        with pytest.raises(ConfigurationError, match="invalid_strategy"):
            DocumentSplitter(settings)

"""Unit tests for SentenceWindowSplitter."""

import tiktoken

from src.ingestion.sentence_window_splitter import SentenceWindowSplitter

# Use cl100k_base for all tests — same as the production default.
_enc = tiktoken.get_encoding("cl100k_base")


def _token_count(text: str) -> int:
    return len(_enc.encode(text))


def _make_splitter(chunk_size: int = 100, chunk_overlap: int = 20) -> SentenceWindowSplitter:
    return SentenceWindowSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=_token_count,
    )


class TestSentenceWindowSplitterBasic:
    def test_multi_sentence_text_produces_chunks(self) -> None:
        splitter = _make_splitter(chunk_size=50, chunk_overlap=10)
        # Build text clearly larger than 50 tokens.
        text = (
            "The quick brown fox jumps over the lazy dog. " * 5
            + "Pack my box with five dozen liquor jugs. " * 5
            + "How vexingly quick daft zebras jump. " * 5
        )
        chunks = splitter.split_text(text)
        assert len(chunks) >= 2

    def test_all_chunks_are_strings(self) -> None:
        splitter = _make_splitter()
        text = "First sentence. Second sentence. Third sentence. " * 10
        chunks = splitter.split_text(text)
        for chunk in chunks:
            assert isinstance(chunk, str)

    def test_chunks_are_not_empty(self) -> None:
        splitter = _make_splitter()
        text = "A meaningful sentence here. Another one follows. " * 10
        chunks = splitter.split_text(text)
        for chunk in chunks:
            assert chunk.strip() != ""

    def test_all_text_content_covered(self) -> None:
        """All sentences from the source text must appear in at least one chunk."""
        splitter = _make_splitter(chunk_size=80, chunk_overlap=15)
        sentences = [
            "The sky is blue.",
            "The grass is green.",
            "Mountains are tall.",
            "Rivers flow down.",
            "Birds sing at dawn.",
            "Fish swim in the sea.",
            "Trees grow slowly.",
            "Wind blows gently.",
        ]
        text = " ".join(sentences)
        chunks = splitter.split_text(text)
        combined = " ".join(chunks)
        for sent in sentences:
            # Each source sentence should appear in the reconstructed output.
            assert sent in combined, f"Sentence not found in any chunk: {sent!r}"


class TestSentenceWindowSplitterEdgeCases:
    def test_single_sentence_returns_one_chunk(self) -> None:
        splitter = _make_splitter(chunk_size=200, chunk_overlap=20)
        # Must be >= 100 chars to pass the minimum-chunk-length filter.
        text = (
            "This is the only sentence in the document and it is long enough "
            "to pass the one hundred character filter threshold."
        )
        assert len(text) >= 100
        chunks = splitter.split_text(text)
        assert len(chunks) == 1
        assert text.strip() in chunks[0]

    def test_empty_text_returns_empty_list(self) -> None:
        splitter = _make_splitter()
        assert splitter.split_text("") == []

    def test_whitespace_only_returns_empty_list(self) -> None:
        splitter = _make_splitter()
        assert splitter.split_text("   \n\n  ") == []

    def test_short_chunks_below_100_chars_discarded(self) -> None:
        splitter = _make_splitter(chunk_size=200, chunk_overlap=10)
        # Single very short sentence — below 100 character threshold.
        chunks = splitter.split_text("Hi.")
        assert chunks == []

    def test_chunk_size_respected(self) -> None:
        """No chunk should exceed chunk_size tokens by more than one sentence's worth."""
        chunk_size = 60
        splitter = _make_splitter(chunk_size=chunk_size, chunk_overlap=5)
        text = (
            "The quick brown fox jumps over the lazy dog every single day. " * 8
        )
        chunks = splitter.split_text(text)
        for chunk in chunks:
            token_count = _token_count(chunk)
            # Allow headroom of one extra sentence (~20 tokens) for boundary cases.
            assert token_count <= chunk_size + 20, (
                f"Chunk has {token_count} tokens, exceeds limit of {chunk_size + 20}"
            )


class TestSentenceWindowSplitterOverlap:
    def test_overlap_causes_sentences_to_repeat(self) -> None:
        """Adjacent windows must share at least one sentence when overlap > 0."""
        splitter = _make_splitter(chunk_size=60, chunk_overlap=30)
        sentences = [
            "Alpha sentence is the first one here today.",
            "Beta sentence comes right after alpha today.",
            "Gamma sentence follows beta in the sequence.",
            "Delta sentence is the fourth in the series.",
            "Epsilon sentence rounds out the fifth entry.",
            "Zeta sentence is the sixth and final entry.",
        ]
        text = " ".join(sentences)
        chunks = splitter.split_text(text)
        if len(chunks) < 2:
            # Not enough content to produce overlap — skip assertion.
            return
        # At least one sentence from chunk[0] must appear in chunk[1].
        import nltk

        first_sents = set(nltk.sent_tokenize(chunks[0]))
        second_sents = set(nltk.sent_tokenize(chunks[1]))
        assert first_sents & second_sents, (
            "No overlap found between adjacent chunks.\n"
            f"Chunk 0: {chunks[0]!r}\nChunk 1: {chunks[1]!r}"
        )

    def test_zero_overlap_no_sentence_repetition(self) -> None:
        """With chunk_overlap=0, no sentence should appear in two consecutive chunks."""
        splitter = _make_splitter(chunk_size=50, chunk_overlap=0)
        sentences = [
            "First independent sentence here for testing purposes today.",
            "Second independent sentence does not overlap the first one.",
            "Third independent sentence is completely separate from others.",
            "Fourth independent sentence concludes this test case here.",
        ]
        text = " ".join(sentences)
        chunks = splitter.split_text(text)
        if len(chunks) < 2:
            return
        import nltk

        seen: set[str] = set()
        for chunk in chunks:
            chunk_sents = set(nltk.sent_tokenize(chunk))
            overlap = seen & chunk_sents
            assert not overlap, f"Sentences repeated across chunks with overlap=0: {overlap}"
            seen.update(chunk_sents)


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


class TestSentenceWindowSplitterErrorPaths:
    def test_sent_tokenize_lookup_error_propagates(self) -> None:
        """If NLTK punkt_tab data is missing, LookupError must propagate to the caller."""
        from unittest.mock import patch

        import pytest

        splitter = _make_splitter()
        with patch("nltk.sent_tokenize", side_effect=LookupError("punkt_tab not found")), pytest.raises(LookupError, match="punkt_tab"):
            splitter.split_text("Some sentence here.")

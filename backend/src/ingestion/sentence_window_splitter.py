"""Sentence-window text splitter using NLTK sentence tokenizer.

Each window groups consecutive sentences up to ``chunk_size`` tokens.
Overlap is achieved by re-including trailing sentences from the previous
window so that adjacent windows share context.
"""

from __future__ import annotations

from collections.abc import Callable

import nltk
from langchain_text_splitters import TextSplitter

nltk.download("punkt_tab", quiet=True)

_MIN_CHUNK_CHARS = 100


class SentenceWindowSplitter(TextSplitter):
    """Split text into sentence-window chunks with token-aware sizing.

    Parameters
    ----------
    chunk_size:
        Maximum number of tokens per window.
    chunk_overlap:
        Approximate number of overlap tokens carried from the previous window.
        Implemented by re-including trailing sentences from the prior window.
    length_function:
        Callable that maps a text string to its token count.
    """

    def __init__(
        self,
        chunk_size: int,
        chunk_overlap: int,
        length_function: Callable[[str], int],
    ) -> None:
        # Pass chunk_size and chunk_overlap to the TextSplitter base so that
        # its internal bookkeeping attributes (_chunk_size, _chunk_overlap) are
        # set correctly; length_function is registered on the base as well.
        super().__init__(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=length_function,
        )
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._length_fn = length_function

    # ------------------------------------------------------------------
    # TextSplitter ABC
    # ------------------------------------------------------------------

    def split_text(self, text: str) -> list[str]:
        """Split *text* into sentence windows and return as a list of strings.

        Steps
        -----
        1. Tokenise into sentences with ``nltk.sent_tokenize``.
        2. Greedily pack sentences into a window up to ``chunk_size`` tokens.
        3. Calculate overlap: walk backward through the completed window to
           find how many trailing sentences fit within ``chunk_overlap`` tokens.
        4. Advance the cursor by ``window_size - overlap_sentences`` (minimum 1)
           so the next window starts from the first non-overlapping sentence.
        5. Discard any window whose stripped text is shorter than 100 characters.
        """
        sentences = nltk.sent_tokenize(text)
        if not sentences:
            return []

        windows: list[str] = []
        i = 0

        while i < len(sentences):
            window: list[str] = []
            token_count = 0
            j = i

            # Greedily fill the window up to chunk_size tokens.
            while j < len(sentences):
                sent_tokens = self._length_fn(sentences[j])
                if token_count + sent_tokens > self._chunk_size and window:
                    break
                window.append(sentences[j])
                token_count += sent_tokens
                j += 1

            chunk_text = " ".join(window).strip()
            if len(chunk_text) >= _MIN_CHUNK_CHARS:
                windows.append(chunk_text)

            # Determine overlap: count tokens backwards from end of window.
            overlap_tokens = 0
            overlap_start = len(window)  # exclusive index of first overlap sentence
            for k in range(len(window) - 1, 0, -1):
                overlap_tokens += self._length_fn(window[k])
                if overlap_tokens >= self._chunk_overlap:
                    overlap_start = k
                    break
            else:
                overlap_start = 0

            # Advance cursor: skip sentences not in the overlap region.
            advance = max(1, overlap_start)
            i += advance

        return windows

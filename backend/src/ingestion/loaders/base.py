"""Abstract base class for all document loaders."""

from abc import ABC, abstractmethod

from src.ingestion.models import Document


class BaseLoader(ABC):
    """Contract that every document loader must satisfy.

    Implementations are responsible for reading source files and returning
    a list of ``Document`` instances.  Splitting, embedding, and upsert are
    handled by later pipeline stages.
    """

    @abstractmethod
    async def load(self) -> list[Document]:
        """Load source documents and return them as a flat list.

        Each item in the returned list represents one logical page or file.
        The ``metadata`` dict must contain at minimum:
        - ``source_path`` (str) — absolute path or blob URL
        - ``filename`` (str) — basename of the file
        - ``file_type`` (str) — ``"pdf"`` or ``"txt"``
        - ``page_number`` (int) — 0-indexed page; ``-1`` if not applicable
        - ``doc_id`` (str) — UUID5 of the source path
        """

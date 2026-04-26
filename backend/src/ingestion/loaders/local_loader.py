"""Local filesystem document loader for PDF and TXT files."""

import asyncio
import uuid
from pathlib import Path
from typing import Any

import pypdf
import structlog

from src.ingestion.loaders.base import BaseLoader
from src.ingestion.models import Document

logger = structlog.get_logger(__name__)

_SUPPORTED_EXTENSIONS = {".pdf", ".txt"}


def _make_doc_id(source_path: str) -> str:
    """Return a deterministic UUID5 for the given absolute path."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, source_path))


class LocalFileLoader(BaseLoader):
    """Load PDF and TXT files from a local directory tree.

    - PDF files are read page-by-page using ``pypdf.PdfReader``.
    - TXT files are read as a single document with ``page_number = -1``.
    - Files with unsupported extensions are skipped with a warning log.
    - Empty files and corrupted PDFs are skipped with an error/warning log.
    """

    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir

    @staticmethod
    def doc_id_for(file_path: Path) -> str:
        """Return the deterministic doc_id for a file path (same as ingestion time)."""
        return _make_doc_id(str(file_path.resolve()))

    def discover_files(self) -> list[Path]:
        """Return sorted list of supported files under ``data_dir``."""
        files: list[Path] = []
        for path in sorted(self._data_dir.rglob("*")):
            if not path.is_file():
                continue
            ext = path.suffix.lower()
            if ext not in _SUPPORTED_EXTENSIONS:
                logger.warning("unsupported_file_extension", path=str(path), extension=ext)
                continue
            files.append(path)
        return files

    async def load_one(self, file_path: Path) -> list[Document]:
        """Load a single file and return its ``Document`` objects."""
        ext = file_path.suffix.lower()
        if ext == ".pdf":
            return await asyncio.to_thread(self._load_pdf, file_path)
        if ext == ".txt":
            return await asyncio.to_thread(self._load_txt, file_path)
        logger.warning("unsupported_file_extension", path=str(file_path), extension=ext)
        return []

    async def load(self) -> list[Document]:
        """Walk ``data_dir`` and return one ``Document`` per page/file."""
        documents: list[Document] = []
        for file_path in self.discover_files():
            documents.extend(await self.load_one(file_path))
        logger.info(
            "local_loader_complete",
            data_dir=str(self._data_dir),
            document_count=len(documents),
        )
        return documents

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_base_metadata(
        self, file_path: Path, file_type: str, page_number: int
    ) -> dict[str, Any]:
        source_path = str(file_path.resolve())
        return {
            "source_path": source_path,
            "filename": file_path.name,
            "file_type": file_type,
            "page_number": page_number,
            "doc_id": _make_doc_id(source_path),
        }

    def _load_pdf(self, file_path: Path) -> list[Document]:
        """Extract text from each page of a PDF file."""
        try:
            reader = pypdf.PdfReader(str(file_path))
        except Exception as exc:
            logger.error(
                "pdf_load_failed",
                path=str(file_path),
                error=str(exc),
            )
            return []

        documents: list[Document] = []
        for page_number, page in enumerate(reader.pages):
            try:
                text = page.extract_text() or ""
            except Exception as exc:
                logger.error(
                    "pdf_page_extract_failed",
                    path=str(file_path),
                    page_number=page_number,
                    error=str(exc),
                )
                continue

            text = text.strip()
            if not text:
                logger.warning(
                    "pdf_blank_page_skipped",
                    path=str(file_path),
                    page_number=page_number,
                )
                continue

            metadata = self._build_base_metadata(file_path, "pdf", page_number)
            documents.append(Document(content=text, metadata=metadata))

        if not documents:
            logger.warning("pdf_no_content", path=str(file_path))

        return documents

    def _load_txt(self, file_path: Path) -> list[Document]:
        """Read a UTF-8 text file as a single Document."""
        try:
            text = file_path.read_text(encoding="utf-8").strip()
        except Exception as exc:
            logger.error(
                "txt_load_failed",
                path=str(file_path),
                error=str(exc),
            )
            return []

        if not text:
            logger.warning("txt_empty_file", path=str(file_path))
            return []

        metadata = self._build_base_metadata(file_path, "txt", -1)
        return [Document(content=text, metadata=metadata)]

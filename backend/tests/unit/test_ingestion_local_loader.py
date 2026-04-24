"""Unit tests for LocalFileLoader.

All filesystem and pypdf interactions are mocked so no real I/O occurs.
"""

import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.ingestion.loaders.local_loader import LocalFileLoader, _make_doc_id

pytestmark = pytest.mark.asyncio


def _fake_file(name: str, suffix: str, parent: Path) -> MagicMock:
    """Return a MagicMock that looks like a Path pointing to a file."""
    p = MagicMock(spec=Path)
    p.is_file.return_value = True
    p.suffix = suffix
    p.name = name
    p.resolve.return_value = p
    p.__str__ = lambda self: str(parent / name)  # type: ignore[method-assign]
    return p


# ---------------------------------------------------------------------------
# _make_doc_id
# ---------------------------------------------------------------------------


class TestMakeDocId:
    def test_deterministic(self) -> None:
        path = "/abs/path/to/file.pdf"
        assert _make_doc_id(path) == _make_doc_id(path)

    def test_different_paths_give_different_ids(self) -> None:
        assert _make_doc_id("/a.pdf") != _make_doc_id("/b.pdf")

    def test_is_valid_uuid(self) -> None:
        result = _make_doc_id("/some/path.txt")
        # Should not raise
        uuid.UUID(result)


# ---------------------------------------------------------------------------
# LocalFileLoader.load — PDF
# ---------------------------------------------------------------------------


class TestLocalFileLoaderPDF:
    @pytest.fixture
    def data_dir(self, tmp_path: Path) -> Path:
        return tmp_path

    def _make_loader(self, data_dir: Path) -> LocalFileLoader:
        return LocalFileLoader(data_dir=data_dir)

    async def test_pdf_pages_loaded(self, data_dir: Path) -> None:
        fake_pdf = data_dir / "manual.pdf"
        fake_pdf.touch()

        page0 = MagicMock()
        page0.extract_text.return_value = "Page zero content with enough characters to pass."
        page1 = MagicMock()
        page1.extract_text.return_value = "Page one content with enough characters to pass."

        mock_reader = MagicMock()
        mock_reader.pages = [page0, page1]

        with patch("src.ingestion.loaders.local_loader.pypdf") as mock_pypdf:
            mock_pypdf.PdfReader.return_value = mock_reader
            loader = self._make_loader(data_dir)
            docs = await loader.load()

        assert len(docs) == 2
        assert docs[0].metadata["page_number"] == 0
        assert docs[1].metadata["page_number"] == 1
        assert docs[0].metadata["file_type"] == "pdf"
        assert docs[0].metadata["filename"] == "manual.pdf"

    async def test_blank_pdf_page_skipped(self, data_dir: Path) -> None:
        fake_pdf = data_dir / "blank.pdf"
        fake_pdf.touch()

        page = MagicMock()
        page.extract_text.return_value = "   "  # blank

        mock_reader = MagicMock()
        mock_reader.pages = [page]

        with patch("src.ingestion.loaders.local_loader.pypdf") as mock_pypdf:
            mock_pypdf.PdfReader.return_value = mock_reader
            loader = self._make_loader(data_dir)
            docs = await loader.load()

        assert docs == []

    async def test_corrupted_pdf_skipped(self, data_dir: Path) -> None:
        fake_pdf = data_dir / "corrupt.pdf"
        fake_pdf.touch()

        with patch("src.ingestion.loaders.local_loader.pypdf") as mock_pypdf:
            mock_pypdf.PdfReader.side_effect = Exception("bad PDF")
            loader = self._make_loader(data_dir)
            docs = await loader.load()

        assert docs == []

    async def test_pdf_doc_id_is_deterministic(self, data_dir: Path) -> None:
        fake_pdf = data_dir / "stable.pdf"
        fake_pdf.touch()

        page = MagicMock()
        page.extract_text.return_value = "Stable content with enough characters here."

        mock_reader = MagicMock()
        mock_reader.pages = [page]

        with patch("src.ingestion.loaders.local_loader.pypdf") as mock_pypdf:
            mock_pypdf.PdfReader.return_value = mock_reader
            loader = self._make_loader(data_dir)
            docs1 = await loader.load()

        with patch("src.ingestion.loaders.local_loader.pypdf") as mock_pypdf:
            mock_pypdf.PdfReader.return_value = mock_reader
            loader2 = self._make_loader(data_dir)
            docs2 = await loader2.load()

        assert docs1[0].metadata["doc_id"] == docs2[0].metadata["doc_id"]


# ---------------------------------------------------------------------------
# LocalFileLoader.load — TXT
# ---------------------------------------------------------------------------


class TestLocalFileLoaderTXT:
    @pytest.fixture
    def data_dir(self, tmp_path: Path) -> Path:
        return tmp_path

    def _make_loader(self, data_dir: Path) -> LocalFileLoader:
        return LocalFileLoader(data_dir=data_dir)

    async def test_txt_file_loaded(self, data_dir: Path) -> None:
        txt_file = data_dir / "notes.txt"
        txt_file.write_text("Some useful content here.", encoding="utf-8")

        loader = self._make_loader(data_dir)
        docs = await loader.load()

        assert len(docs) == 1
        assert docs[0].metadata["file_type"] == "txt"
        assert docs[0].metadata["page_number"] == -1
        assert docs[0].metadata["filename"] == "notes.txt"
        assert docs[0].content == "Some useful content here."

    async def test_empty_txt_skipped(self, data_dir: Path) -> None:
        txt_file = data_dir / "empty.txt"
        txt_file.write_text("   ", encoding="utf-8")

        loader = self._make_loader(data_dir)
        docs = await loader.load()

        assert docs == []

    async def test_txt_doc_id_in_metadata(self, data_dir: Path) -> None:
        txt_file = data_dir / "file.txt"
        txt_file.write_text("Content that is present.", encoding="utf-8")

        loader = self._make_loader(data_dir)
        docs = await loader.load()

        assert "doc_id" in docs[0].metadata
        uuid.UUID(str(docs[0].metadata["doc_id"]))  # must be valid UUID


# ---------------------------------------------------------------------------
# LocalFileLoader.load — unsupported extension
# ---------------------------------------------------------------------------


class TestLocalFileLoaderUnsupported:
    async def test_unsupported_extension_skipped(self, tmp_path: Path) -> None:
        (tmp_path / "image.png").touch()
        loader = LocalFileLoader(data_dir=tmp_path)
        docs = await loader.load()
        assert docs == []

    async def test_mixed_files_only_supported_loaded(self, tmp_path: Path) -> None:
        (tmp_path / "doc.txt").write_text("Valid content here.", encoding="utf-8")
        (tmp_path / "image.png").touch()

        loader = LocalFileLoader(data_dir=tmp_path)
        docs = await loader.load()

        assert len(docs) == 1
        assert docs[0].metadata["filename"] == "doc.txt"

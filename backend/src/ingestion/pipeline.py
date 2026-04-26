"""Ingestion pipeline: load → chunk → embed → upsert → BM25 index."""

import time
from pathlib import Path

import structlog
from pydantic import BaseModel

from src.config import Settings
from src.exceptions import EmbeddingError, IngestionError
from src.ingestion.bm25_store import BM25Store
from src.ingestion.embedder import Embedder
from src.ingestion.loaders.local_loader import LocalFileLoader
from src.ingestion.splitter import DocumentSplitter
from src.ingestion.vector_store import QdrantVectorStore

logger = structlog.get_logger(__name__)


class PipelineResult(BaseModel):
    """Summary of a completed ingestion pipeline run."""

    docs_processed: int
    """Number of raw document pages/files successfully loaded."""

    chunks_created: int
    """Total chunks that were embedded and upserted successfully."""

    errors: list[str]
    """Per-file error messages; pipeline continues on individual failures."""

    duration_ms: float
    """Wall-clock time for the full pipeline run in milliseconds."""


async def run_pipeline(
    data_dir: Path,
    settings: Settings,
    bm25_store: BM25Store | None = None,
) -> PipelineResult:
    """Run the full document ingestion pipeline, processing one file at a time.

    Stages per file:
    1. Load the file with ``LocalFileLoader``.
    2. Split into chunks with ``DocumentSplitter``.
    3. Embed with ``Embedder`` (async batched Azure OpenAI calls).
    4. Upsert the file's points into Qdrant.

    After all files:
    5. Build BM25 index from all successfully upserted chunks and persist.

    ``ensure_collection`` is called once before the file loop.
    Per-file errors are collected in ``PipelineResult.errors`` and do not
    abort the run — other files continue to be processed.
    """
    pipeline_start = time.monotonic()
    errors: list[str] = []
    all_embedded_chunks: list = []
    total_docs = 0

    loader = LocalFileLoader(data_dir=data_dir)
    splitter = DocumentSplitter(settings=settings)
    embedder = Embedder(settings=settings)
    vector_store = QdrantVectorStore(settings=settings)

    # Discover files before touching the network so an empty dir returns fast.
    file_paths = loader.discover_files()
    if not file_paths:
        logger.info("pipeline_no_files_found", data_dir=str(data_dir))
        return PipelineResult(
            docs_processed=0,
            chunks_created=0,
            errors=errors,
            duration_ms=(time.monotonic() - pipeline_start) * 1000,
        )

    # Ensure collection exists once; a failure here aborts the whole run.
    try:
        await vector_store.ensure_collection()
    except Exception as exc:
        logger.error("pipeline_ensure_collection_failed", error=str(exc))
        await vector_store.close()
        return PipelineResult(
            docs_processed=0,
            chunks_created=0,
            errors=[f"Collection setup failed: {exc}"],
            duration_ms=(time.monotonic() - pipeline_start) * 1000,
        )

    try:
        for file_path in file_paths:
            file_name = file_path.name
            doc_id = loader.doc_id_for(file_path)

            if await vector_store.doc_exists(doc_id):
                logger.info("pipeline_file_skipped", file=file_name, doc_id=doc_id)
                continue

            # Stage 1: Load
            file_docs = await loader.load_one(file_path)
            if not file_docs:
                logger.warning("pipeline_file_no_content", file=file_name)
                continue
            total_docs += len(file_docs)

            # Stage 2: Split
            chunks = splitter.split(file_docs)
            if not chunks:
                logger.warning("pipeline_file_no_chunks", file=file_name)
                continue

            # Stage 3: Embed
            try:
                embedded = await embedder.embed_chunks(chunks)
            except (EmbeddingError, Exception) as exc:
                logger.error("pipeline_file_embed_failed", file=file_name, error=str(exc))
                errors.append(f"{file_name}: embedding failed: {exc}")
                continue

            # Stage 4: Upsert
            try:
                await vector_store.upsert(embedded)
            except IngestionError as exc:
                logger.error("pipeline_file_upsert_failed", file=file_name, error=str(exc))
                errors.append(f"{file_name}: upsert failed: {exc}")
                continue

            all_embedded_chunks.extend(embedded)
            logger.info(
                "pipeline_file_complete",
                file=file_name,
                docs=len(file_docs),
                chunks=len(embedded),
            )
    finally:
        await vector_store.close()

    if not all_embedded_chunks:
        logger.warning("pipeline_no_chunks_upserted")
        return PipelineResult(
            docs_processed=total_docs,
            chunks_created=0,
            errors=errors,
            duration_ms=(time.monotonic() - pipeline_start) * 1000,
        )

    # Stage 5: BM25 — built once from all successfully upserted chunks.
    if bm25_store is None:
        bm25_store = BM25Store(index_path=Path(settings.bm25_index_path))
    try:
        bm25_store.build(all_embedded_chunks)
        bm25_store.save()
    except Exception as exc:
        logger.error("pipeline_bm25_failed", error=str(exc))
        errors.append(f"BM25 stage failed: {exc}")

    total_ms = (time.monotonic() - pipeline_start) * 1000
    logger.info(
        "pipeline_complete",
        docs_processed=total_docs,
        chunks_created=len(all_embedded_chunks),
        error_count=len(errors),
        total_duration_ms=round(total_ms, 1),
    )

    return PipelineResult(
        docs_processed=total_docs,
        chunks_created=len(all_embedded_chunks),
        errors=errors,
        duration_ms=total_ms,
    )


if __name__ == "__main__":
    import asyncio

    from src.config import get_settings

    _settings = get_settings()
    result = asyncio.run(run_pipeline(Path(_settings.data_dir), _settings))
    logger.info("pipeline_complete", **result.model_dump())

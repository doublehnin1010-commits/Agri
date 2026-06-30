from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import BinaryIO

from fastapi import UploadFile

from app.services.embedding_service import (
    build_embedding_documents,
    upsert_embedding_documents,
)
from app.services.metadata_service import generate_metadata_for_dataset
from app.services.reindex import read_docx_lines_from_stream


logger = logging.getLogger(__name__)


class ImportValidationError(ValueError):
    """Raised when uploaded dataset files fail validation."""


@dataclass(frozen=True)
class ImportResult:
    """Summary returned by the DOCX ingestion pipeline."""

    success: bool
    documents_imported: int
    embeddings_created: int
    failed: int
    processing_time_seconds: float


def _validate_docx_upload(file: UploadFile | None, label: str) -> UploadFile:
    """Validate a required DOCX upload by presence and extension."""

    if file is None or not file.filename:
        raise ImportValidationError(f"{label} file is required")

    if not file.filename.lower().endswith(".docx"):
        raise ImportValidationError(f"{label} must be a .docx file")

    return file


def _read_docx_lines(file_stream: BinaryIO) -> list[str]:
    """Read non-empty DOCX paragraphs from an upload stream."""

    return read_docx_lines_from_stream(file_stream)


async def _read_uploaded_docx(file: UploadFile) -> list[str]:
    """Read an uploaded DOCX file without blocking the event loop."""

    return await asyncio.to_thread(_read_docx_lines, file.file)


def _merge_docx_rows(
    proverbs: list[str],
    meanings: list[str],
    english_meanings: list[str],
) -> list[tuple[str, str, str]]:
    """Merge proverb, meaning, and English meaning paragraphs by index."""

    counts = {
        "Proverbs.docx": len(proverbs),
        "Meanings.docx": len(meanings),
        "EnglishMeanings.docx": len(english_meanings),
    }
    if len(set(counts.values())) != 1:
        details = ", ".join(f"{name}={count}" for name, count in counts.items())
        raise ImportValidationError(
            "Uploaded DOCX files must have the same number of non-empty paragraphs "
            f"({details})"
        )

    return list(zip(proverbs, meanings, english_meanings))


async def import_docx(
    proverbs_file: UploadFile | None,
    meanings_file: UploadFile | None,
    english_meanings_file: UploadFile | None,
) -> ImportResult:
    """Run the production DOCX ingestion pipeline into ChromaDB."""

    started_at = time.perf_counter()

    validated_proverbs = _validate_docx_upload(proverbs_file, "Proverbs")
    validated_meanings = _validate_docx_upload(meanings_file, "Meanings")
    validated_english_meanings = _validate_docx_upload(
        english_meanings_file,
        "EnglishMeanings",
    )

    logger.info("Reading Proverbs.docx...")
    logger.info("Reading Meanings.docx...")
    logger.info("Reading EnglishMeanings.docx...")
    proverbs, meanings, english_meanings = await asyncio.gather(
        _read_uploaded_docx(validated_proverbs),
        _read_uploaded_docx(validated_meanings),
        _read_uploaded_docx(validated_english_meanings),
    )

    logger.info("Validating...")
    rows = _merge_docx_rows(proverbs, meanings, english_meanings)

    logger.info("Generating metadata...")
    metadata_rows = await generate_metadata_for_dataset(rows)
    failed = sum(1 for item in metadata_rows if item.failed)

    logger.info("Embedding...")
    documents = build_embedding_documents(rows, metadata_rows)

    logger.info("Saving to ChromaDB...")
    embeddings_created = await upsert_embedding_documents(documents)

    elapsed = round(time.perf_counter() - started_at, 2)
    logger.info("Completed.")

    return ImportResult(
        success=True,
        documents_imported=len(rows),
        embeddings_created=embeddings_created,
        failed=failed,
        processing_time_seconds=elapsed,
    )

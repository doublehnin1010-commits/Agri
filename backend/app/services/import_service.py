from __future__ import annotations

import asyncio
import logging
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

from fastapi import BackgroundTasks, UploadFile

from app.core.config import BACKEND_DIR
from app.readers import DatasetRows, DocxReader, DocumentReader, TxtReader
from app.services.embedding_service import (
    build_embedding_documents,
    upsert_embedding_documents,
)
from app.services.job_service import job_service
from app.services.metadata_service import (
    generate_metadata_for_batch,
    metadata_batch_size,
    metadata_max_concurrent,
)


LOG_DIR = BACKEND_DIR / "logs"
UPLOAD_DIR = BACKEND_DIR / "uploaded_imports"


logger = logging.getLogger("import_jobs")
logger.setLevel(logging.INFO)
if not any(isinstance(handler, logging.FileHandler) for handler in logger.handlers):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(LOG_DIR / "import_jobs.log", encoding="utf-8")
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    )
    logger.addHandler(file_handler)


class ImportValidationError(ValueError):
    """Raised when uploaded dataset files fail validation."""


@dataclass(frozen=True)
class ImportUploadResult:
    job_id: str
    status: str
    message: str


READERS: dict[str, DocumentReader] = {
    "docx": DocxReader(),
    "txt": TxtReader(),
}


def _normalize_dataset_type(dataset_type: str | None) -> str:
    normalized = (dataset_type or "docx").strip().lower()
    if normalized not in READERS:
        raise ImportValidationError("Only DOCX or TXT files are supported.")
    return normalized


def _validate_upload(file: UploadFile | None, extension: str) -> UploadFile:
    """Validate a required dataset upload by presence and extension."""

    if file is None or not file.filename:
        raise ImportValidationError("Missing required files.")

    if not file.filename.lower().endswith(extension):
        raise ImportValidationError("Only DOCX or TXT files are supported.")

    return file


def _save_upload_sync(upload: UploadFile, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    upload.file.seek(0)
    with destination.open("wb") as output:
        shutil.copyfileobj(upload.file, output, length=1024 * 1024)


async def _save_upload(upload: UploadFile, destination: Path) -> None:
    await asyncio.to_thread(_save_upload_sync, upload, destination)


def _merge_rows(dataset: DatasetRows, extension: str) -> list[tuple[str, str, str]]:
    """Merge proverb, meaning, and English meaning records by index."""

    counts = {
        f"Proverbs{extension}": len(dataset.proverbs),
        f"Meanings{extension}": len(dataset.meanings),
        f"EnglishMeanings{extension}": len(dataset.english_meanings),
    }
    if any(count == 0 for count in counts.values()):
        raise ImportValidationError("Uploaded files must not be empty.")

    if len(set(counts.values())) != 1:
        details = ", ".join(f"{name}={count}" for name, count in counts.items())
        raise ImportValidationError(f"Record counts do not match. ({details})")

    return list(zip(dataset.proverbs, dataset.meanings, dataset.english_meanings))


async def start_import(
    proverbs_file: UploadFile | None,
    meanings_file: UploadFile | None,
    english_meanings_file: UploadFile | None,
    background_tasks: BackgroundTasks,
    dataset_type: str | None = "docx",
) -> ImportUploadResult:
    """Validate and persist uploaded files, then enqueue background ingestion."""

    normalized_dataset_type = _normalize_dataset_type(dataset_type)
    reader = READERS[normalized_dataset_type]
    extension = reader.extension

    validated_proverbs = _validate_upload(proverbs_file, extension)
    validated_meanings = _validate_upload(meanings_file, extension)
    validated_english_meanings = _validate_upload(
        english_meanings_file,
        extension,
    )

    job = job_service.create_job()
    job_upload_dir = UPLOAD_DIR / job.job_id
    proverbs_path = job_upload_dir / f"Proverbs{extension}"
    meanings_path = job_upload_dir / f"Meanings{extension}"
    english_meanings_path = job_upload_dir / f"EnglishMeanings{extension}"

    await asyncio.gather(
        _save_upload(validated_proverbs, proverbs_path),
        _save_upload(validated_meanings, meanings_path),
        _save_upload(validated_english_meanings, english_meanings_path),
    )

    logger.info("Job %s uploaded files and queued processing.", job.job_id)
    background_tasks.add_task(
        process_import_job,
        job.job_id,
        normalized_dataset_type,
        proverbs_path,
        meanings_path,
        english_meanings_path,
    )

    return ImportUploadResult(
        job_id=job.job_id,
        status=job.status,
        message="Dataset uploaded successfully. Processing started.",
    )


async def process_import_job(
    job_id: str,
    dataset_type: str,
    proverbs_path: Path,
    meanings_path: Path,
    english_meanings_path: Path,
) -> None:
    """Run the ingestion pipeline for a queued import job."""

    started_at = time.perf_counter()
    logger.info("Job %s started.", job_id)

    try:
        reader = READERS[_normalize_dataset_type(dataset_type)]

        job_service.update_job(job_id, status="processing", step="Reading files...")
        dataset = await asyncio.to_thread(
            reader.read_dataset,
            proverbs_path,
            meanings_path,
            english_meanings_path,
        )

        job_service.update_job(job_id, step="Validating...")
        rows = _merge_rows(dataset, reader.extension)
        total = len(rows)
        job_service.update_job(job_id, total=total, current=0, step="Generating metadata...")

        logger.info("Job %s generating metadata for %s records.", job_id, total)

        indexed_rows = [
            (row_number, proverb, meaning, english_meaning)
            for row_number, (proverb, meaning, english_meaning) in enumerate(rows, start=1)
        ]
        batches = [
            indexed_rows[index : index + metadata_batch_size()]
            for index in range(0, len(indexed_rows), metadata_batch_size())
        ]

        semaphore = asyncio.Semaphore(metadata_max_concurrent())
        embed_lock = asyncio.Lock()
        metadata_processed = 0
        embeddings_created = 0
        failed = 0
        embedding_started = False

        async def process_batch(
            batch: list[tuple[int, str, str, str]],
            *,
            batch_index: int,
        ) -> None:
            nonlocal metadata_processed, embeddings_created, failed, embedding_started

            batch_result = await generate_metadata_for_batch(
                batch,
                semaphore=semaphore,
                batch_index=batch_index,
            )
            batch_failed = sum(1 for _, metadata in batch_result if metadata.failed)

            metadata_processed += len(batch_result)
            failed += batch_failed
            job_service.update_job(
                job_id,
                status="processing",
                metadata_current=metadata_processed,
                failed=failed,
                step="Generating metadata...",
            )

            batch_rows = [rows[row_number - 1] for row_number, *_ in batch]
            batch_metadata = [metadata for _, metadata in batch_result]
            documents = build_embedding_documents(batch_rows, batch_metadata)

            if not embedding_started:
                embedding_started = True
                job_service.update_job(
                    job_id,
                    status="embedding",
                    failed=failed,
                    step="Generating embeddings...",
                )

            async with embed_lock:
                batch_embed_base = embeddings_created
                saved = await upsert_embedding_documents(
                    documents,
                    progress_callback=lambda saved_count, _: job_service.update_job(
                        job_id,
                        status="embedding",
                        embed_current=batch_embed_base + saved_count,
                        failed=failed,
                        step="Saving to ChromaDB...",
                    ),
                )

            embeddings_created += saved
            job_service.update_job(
                job_id,
                status="embedding",
                embed_current=embeddings_created,
                failed=failed,
                step="Saving to ChromaDB...",
            )

        batch_tasks = [
            asyncio.create_task(process_batch(batch, batch_index=batch_index))
            for batch_index, batch in enumerate(batches, start=1)
        ]
        for task in asyncio.as_completed(batch_tasks):
            await task

        elapsed = round(time.perf_counter() - started_at, 2)
        job_service.update_job(
            job_id,
            status="completed",
            metadata_current=total,
            embed_current=total,
            total=total,
            documents=embeddings_created,
            failed=failed,
            processing_time_seconds=elapsed,
            step="Completed",
        )
        logger.info(
            "Job %s completed in %s seconds. documents=%s failed=%s",
            job_id,
            elapsed,
            embeddings_created,
            failed,
        )
    except Exception as exc:
        elapsed = round(time.perf_counter() - started_at, 2)
        job_service.update_job(
            job_id,
            status="failed",
            step="Failed",
            error=str(exc),
            processing_time_seconds=elapsed,
        )
        logger.exception("Job %s failed after %s seconds.", job_id, elapsed)

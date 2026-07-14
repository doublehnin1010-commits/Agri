from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from app.core.config import BACKEND_DIR


JOB_STATUSES = {"uploaded", "processing", "embedding", "completed", "failed"}
JOB_DIR = BACKEND_DIR / "import_jobs"


@dataclass
class ImportJob:
    job_id: str
    status: str
    current: int = 0
    total: int = 0
    progress: float = 0.0
    step: str = "Uploading"
    failed: int = 0
    documents: int = 0
    processing_time_seconds: float | None = None
    estimated_remaining: int = 0
    metadata_current: int = 0
    embed_current: int = 0
    error: str | None = None
    created_at: float = 0.0
    updated_at: float = 0.0


class ImportJobService:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._jobs: dict[str, ImportJob] = {}
        JOB_DIR.mkdir(parents=True, exist_ok=True)

    def create_job(self, *, total: int = 0) -> ImportJob:
        now = time.time()
        job = ImportJob(
            job_id=uuid.uuid4().hex,
            status="uploaded",
            total=total,
            step="Uploading",
            created_at=now,
            updated_at=now,
        )
        with self._lock:
            self._jobs[job.job_id] = job
            self._persist(job)
        return job

    def update_job(self, job_id: str, **changes: Any) -> ImportJob:
        with self._lock:
            job = self.get_job(job_id)
            for key, value in changes.items():
                if hasattr(job, key):
                    setattr(job, key, value)

            if job.total > 0:
                combined = job.metadata_current + job.embed_current
                job.progress = round(min(100.0, (combined / (job.total * 2)) * 100), 1)
                job.current = combined
                job.estimated_remaining = max((job.total * 2) - combined, 0)
            elif job.status == "completed":
                job.progress = 100.0
                job.estimated_remaining = 0

            job.updated_at = time.time()
            self._jobs[job_id] = job
            self._persist(job)
            return job

    def get_job(self, job_id: str) -> ImportJob:
        with self._lock:
            cached = self._jobs.get(job_id)
            if cached is not None:
                return cached

            path = self._job_path(job_id)
            if not path.exists():
                raise KeyError(job_id)

            payload = json.loads(path.read_text(encoding="utf-8"))
            job = ImportJob(**payload)
            self._jobs[job_id] = job
            return job

    def serialize(self, job: ImportJob) -> dict[str, Any]:
        payload = asdict(job)
        if payload["status"] == "completed":
            return {
                "success": True,
                "job_id": job.job_id,
                "status": job.status,
                "documents_imported": job.documents,
                "embeddings_created": job.documents,
                "documents": job.documents,
                "failed": job.failed,
                "processing_time_seconds": job.processing_time_seconds,
            }
        if payload["status"] == "failed":
            return {
                "job_id": job.job_id,
                "status": job.status,
                "current": job.current,
                "total": job.total,
                "progress": job.progress,
                "step": job.step,
                "failed": job.failed,
                "error": job.error,
            }
        return {
            "job_id": job.job_id,
            "status": job.status,
            "current": job.embed_current if job.status == "embedding" else job.metadata_current,
            "total": job.total,
            "progress": job.progress,
            "step": job.step,
            "failed": job.failed,
            "estimated_remaining": max(job.total - (job.embed_current if job.status == "embedding" else job.metadata_current), 0),
        }

    def _persist(self, job: ImportJob) -> None:
        self._job_path(job.job_id).write_text(
            json.dumps(asdict(job), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _job_path(job_id: str) -> Path:
        return JOB_DIR / f"{job_id}.json"


job_service = ImportJobService()

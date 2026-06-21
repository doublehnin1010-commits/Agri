from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.core.config import settings
from app.core.deps import require_admin
from app.services.reindex import read_docx_lines_from_stream
from app.services.rag import upsert_proverbs


router = APIRouter()


def _validate_docx_upload(file: UploadFile, label: str) -> None:
    if not file.filename:
        raise HTTPException(status_code=400, detail=f"{label} file is required")

    if not file.filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail=f"{label} must be a .docx file")


def _build_rows_from_docx_uploads(
    proverbs_file: UploadFile, meanings_file: UploadFile
) -> tuple[list[dict[str, Any]], list[str]]:
    proverbs = read_docx_lines_from_stream(proverbs_file.file)
    meanings = read_docx_lines_from_stream(meanings_file.file)

    warnings: list[str] = []
    if len(proverbs) != len(meanings):
        raise ValueError(
            f"Proverbs and meanings count must match: proverbs={len(proverbs)} meanings={len(meanings)}"
        )

    rows = [
        {"keyword": "", "proverb": proverb, "meaning": meaning, "example": ""}
        for proverb, meaning in zip(proverbs, meanings)
    ]

    if not rows:
        warnings.append("No valid rows found in uploaded Word files.")

    return rows, warnings


@router.post("/import-docx")
async def import_docx(
    proverbs_file: UploadFile = File(...),
    meanings_file: UploadFile = File(...),
    _admin=Depends(require_admin),
):
    _validate_docx_upload(proverbs_file, "Proverbs")
    _validate_docx_upload(meanings_file, "Meanings")

    try:
        rows, warnings = _build_rows_from_docx_uploads(proverbs_file, meanings_file)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read Word files: {e}")

    inserted, skipped = upsert_proverbs(rows)
    return {
        "inserted": inserted,
        "skipped": skipped,
        "warnings": warnings,
        "collection": settings.chroma_collection_name,
    }

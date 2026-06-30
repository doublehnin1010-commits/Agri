from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.core.deps import require_admin
from app.services import import_service
from app.services.import_service import ImportValidationError


router = APIRouter()


@router.post("/import-docx")
async def import_docx(
    proverbs_file: UploadFile | None = File(None),
    meanings_file: UploadFile | None = File(None),
    english_meanings_file: UploadFile | None = File(None),
    _admin=Depends(require_admin),
):
    try:
        result = await import_service.import_docx(
            proverbs_file,
            meanings_file,
            english_meanings_file,
        )
    except ImportValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to import Word files: {e}")

    return {
        "success": result.success,
        "documents_imported": result.documents_imported,
        "embeddings_created": result.embeddings_created,
        "failed": result.failed,
        "processing_time_seconds": result.processing_time_seconds,
    }

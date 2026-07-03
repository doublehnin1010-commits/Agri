from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile

from app.core.deps import require_admin
from app.services import import_service
from app.services.import_service import ImportValidationError
from app.services.job_service import job_service


router = APIRouter()


@router.post("/import-docx")
async def import_docx(
    background_tasks: BackgroundTasks,
    proverbs_file: UploadFile | None = File(None),
    meanings_file: UploadFile | None = File(None),
    english_meanings_file: UploadFile | None = File(None),
    _admin=Depends(require_admin),
):
    try:
        result = await import_service.start_import(
            proverbs_file,
            meanings_file,
            english_meanings_file,
            background_tasks,
        )
    except ImportValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to import Word files: {e}")

    return {
        "job_id": result.job_id,
        "status": result.status,
        "message": result.message,
    }


@router.get("/import-docx/status/{job_id}")
async def import_docx_status(
    job_id: str,
    _admin=Depends(require_admin),
):
    try:
        job = job_service.get_job(job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Import job not found")

    return job_service.serialize(job)

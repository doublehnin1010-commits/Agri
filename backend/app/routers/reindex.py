from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app.services.reindex import (
    reindex_from_word_files,
    reindex_from_word_uploads,
)


router = APIRouter()


class ReindexRequest(BaseModel):
    proverbs_path: str
    meanings_path: str
    clear_existing: bool = True


@router.post("/reindex")
async def reindex(req: ReindexRequest):
    try:
        result = reindex_from_word_files(req.proverbs_path, req.meanings_path, req.clear_existing)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"ok": True, **result}


@router.post("/reindex/upload")
async def reindex_upload(
    proverbs_file: UploadFile = File(...),
    meanings_file: UploadFile = File(...),
    clear_existing: bool = Form(True),
):
    try:
        result = reindex_from_word_uploads(proverbs_file, meanings_file, clear_existing)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"ok": True, **result}

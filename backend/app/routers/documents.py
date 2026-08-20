from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile

from app.core.deps import require_admin
from app.models.document import AgricultureDocument, DocumentListResponse, DocumentUploadResponse
from app.services.document_service import (
    DocumentValidationError,
    delete_document,
    get_document,
    list_documents,
    reprocess_document,
    upload_document,
)

router = APIRouter()


@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_agriculture_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    _admin=Depends(require_admin),
):
    try:
        return await upload_document(file, background_tasks)
    except DocumentValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/documents", response_model=DocumentListResponse)
async def get_agriculture_documents(_admin=Depends(require_admin)):
    return {"documents": await list_documents()}


@router.get("/documents/{document_id}", response_model=AgricultureDocument)
async def get_agriculture_document(document_id: str, _admin=Depends(require_admin)):
    item = await get_document(document_id)
    if not item:
        raise HTTPException(status_code=404, detail="Document not found")
    return item


@router.delete("/documents/{document_id}")
async def delete_agriculture_document(document_id: str, _admin=Depends(require_admin)):
    if not await delete_document(document_id):
        raise HTTPException(status_code=404, detail="Document not found")
    return {"success": True, "deleted": 1}


@router.post("/documents/{document_id}/process")
async def process_agriculture_document(document_id: str, background_tasks: BackgroundTasks, _admin=Depends(require_admin)):
    if not await reprocess_document(document_id, background_tasks):
        raise HTTPException(status_code=404, detail="Document not found")
    return {"success": True, "status": "processing"}

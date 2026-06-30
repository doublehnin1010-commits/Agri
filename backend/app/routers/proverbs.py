from fastapi import APIRouter, Depends, HTTPException

from app.core.deps import require_admin
from app.models.proverb import ProverbCreate, ProverbResponse, ProverbUpdate
from app.services.rag import add_proverb, delete_all_proverbs, delete_proverb, list_proverbs, update_proverb


router = APIRouter()


@router.get("/proverbs", response_model=list[ProverbResponse])
async def get_proverbs(limit: int = 500, offset: int = 0, _admin=Depends(require_admin)):
    return [ProverbResponse(**item) for item in list_proverbs(limit=limit, offset=offset)]


@router.post("/proverbs", response_model=ProverbResponse)
async def create_proverb(payload: ProverbCreate, _admin=Depends(require_admin)):
    try:
        proverb = add_proverb(payload.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return ProverbResponse(**proverb)


@router.put("/proverbs/{proverb_id}", response_model=ProverbResponse)
async def update_proverb_route(proverb_id: str, payload: ProverbUpdate, _admin=Depends(require_admin)):
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    try:
        proverb = update_proverb(proverb_id, updates)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return ProverbResponse(**proverb)


@router.delete("/proverbs/{proverb_id}")
async def delete_proverb_route(proverb_id: str, _admin=Depends(require_admin)):
    deleted = delete_proverb(proverb_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Proverb not found")

    return {"success": True, "deleted": 1}


@router.delete("/proverbs")
async def delete_all_proverbs_route(_admin=Depends(require_admin)):
    deleted = delete_all_proverbs()
    return {"success": True, "deleted": deleted}

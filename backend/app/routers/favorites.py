from fastapi import APIRouter, Depends, HTTPException, status

from app.core.deps import get_current_user_id
from app.models.favorite import FavoriteProverbResponse, FavoriteStatusResponse
from app.services.favorite_service import add_favorite, is_favorite, list_favorites, remove_favorite


router = APIRouter()


@router.post("/favorites/{proverb_id}", response_model=FavoriteStatusResponse)
async def add_favorite_route(proverb_id: str, user_id: str = Depends(get_current_user_id)):
    try:
        await add_favorite(user_id, proverb_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return FavoriteStatusResponse(message="Added to favorites", favorite=True)


@router.delete("/favorites/{proverb_id}", response_model=FavoriteStatusResponse)
async def remove_favorite_route(proverb_id: str, user_id: str = Depends(get_current_user_id)):
    await remove_favorite(user_id, proverb_id)
    return FavoriteStatusResponse(message="Removed from favorites", favorite=False)


@router.get("/favorites", response_model=list[FavoriteProverbResponse])
async def list_favorites_route(user_id: str = Depends(get_current_user_id)):
    return [FavoriteProverbResponse(**item) for item in await list_favorites(user_id)]


@router.get("/favorites/check/{proverb_id}", response_model=FavoriteStatusResponse)
async def check_favorite_route(proverb_id: str, user_id: str = Depends(get_current_user_id)):
    return FavoriteStatusResponse(favorite=await is_favorite(user_id, proverb_id))

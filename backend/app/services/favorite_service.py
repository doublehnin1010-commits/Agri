from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pymongo import ASCENDING, DESCENDING

from app.db.chroma import get_vectorstore
from app.db.mongodb import get_db


COLLECTION = "favorite_proverbs"


async def configure_favorites() -> None:
    db = get_db()
    await db[COLLECTION].create_index(
        [("user_id", ASCENDING), ("proverb_id", ASCENDING)],
        unique=True,
        name="uniq_user_proverb_favorite",
    )
    await db[COLLECTION].create_index(
        [("user_id", ASCENDING), ("created_at", DESCENDING)],
        name="user_favorites_created_at",
    )


async def add_favorite(user_id: str, proverb_id: str) -> None:
    _get_proverb_metadata_or_none(proverb_id, require=True)
    db = get_db()
    await db[COLLECTION].update_one(
        {"user_id": user_id, "proverb_id": proverb_id},
        {"$setOnInsert": {"user_id": user_id, "proverb_id": proverb_id, "created_at": datetime.now(timezone.utc)}},
        upsert=True,
    )


async def remove_favorite(user_id: str, proverb_id: str) -> None:
    db = get_db()
    await db[COLLECTION].delete_one({"user_id": user_id, "proverb_id": proverb_id})


async def is_favorite(user_id: str, proverb_id: str) -> bool:
    db = get_db()
    item = await db[COLLECTION].find_one({"user_id": user_id, "proverb_id": proverb_id}, {"_id": 1})
    return item is not None


async def list_favorites(user_id: str) -> list[dict[str, Any]]:
    db = get_db()
    favorite_rows = await (
        db[COLLECTION]
        .find({"user_id": user_id}, {"_id": 0, "proverb_id": 1, "created_at": 1})
        .sort("created_at", DESCENDING)
        .to_list(length=500)
    )
    if not favorite_rows:
        return []

    proverb_ids = [row["proverb_id"] for row in favorite_rows]
    proverb_map = _get_proverb_metadata_map(proverb_ids)
    items: list[dict[str, Any]] = []
    missing_ids: list[str] = []

    for favorite in favorite_rows:
        proverb_id = favorite["proverb_id"]
        metadata = proverb_map.get(proverb_id)
        if not metadata:
            missing_ids.append(proverb_id)
            continue
        items.append(
            {
                "id": proverb_id,
                "proverb": metadata.get("proverb") or "",
                "meaning": metadata.get("meaning"),
                "english_meaning": metadata.get("english_meaning"),
                "category": metadata.get("category") or metadata.get("keyword"),
                "keyword": metadata.get("keyword"),
                "example": metadata.get("example"),
                "created_at": favorite["created_at"],
            }
        )

    if missing_ids:
        await db[COLLECTION].delete_many({"user_id": user_id, "proverb_id": {"$in": missing_ids}})

    return items


def _get_proverb_metadata_map(proverb_ids: list[str]) -> dict[str, dict[str, Any]]:
    if not proverb_ids:
        return {}
    result = get_vectorstore()._collection.get(ids=proverb_ids, include=["metadatas"])
    ids = result.get("ids") or []
    metadatas = result.get("metadatas") or []
    return {proverb_id: metadata for proverb_id, metadata in zip(ids, metadatas) if metadata}


def _get_proverb_metadata_or_none(proverb_id: str, *, require: bool = False) -> dict[str, Any] | None:
    result = get_vectorstore()._collection.get(ids=[proverb_id], include=["metadatas"])
    metadatas = result.get("metadatas") or []
    metadata = metadatas[0] if metadatas else None
    if require and not metadata:
        raise ValueError("Proverb not found")
    return metadata

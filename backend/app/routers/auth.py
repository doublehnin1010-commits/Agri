from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, HTTPException, status

from app.core.config import settings
from app.core.roles import Role
from app.core.security import create_access_token, hash_password, verify_password
from app.db.mongodb import get_db
from app.models.user import LoginRequest, TokenResponse, UserCreate, UserPublic


router = APIRouter()


def _resolve_role(email: str) -> Role:
    if settings.admin_email and email.lower() == settings.admin_email.lower():
        return Role.ADMIN
    return Role.USER


async def ensure_admin_user():
    db = get_db()
    users = db["users"]

    email = settings.admin_email.strip().lower()
    password = settings.admin_password

    if not email or not password:
        return

    existing = await users.find_one({"email": email})

    if existing:
        return

    doc = {
        "email": email,
        "name": "Administrator",
        "password_hash": hash_password(password),
        "role": Role.ADMIN.value,
        "created_at": datetime.now(timezone.utc),
    }

    result = await users.insert_one(doc)
    if not result:
        return None
    return UserPublic(id=str(result.inserted_id), email=doc["email"], name=doc["name"], role=Role.ADMIN)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest):
    db = get_db()
    users = db["users"]

    user = await users.find_one({"email": payload.email.lower()})
    if not user or not verify_password(payload.password, user.get("password_hash", "")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    role = Role(user.get("role", Role.USER.value))
    token = create_access_token(
        subject=str(user["_id"]),
        extra={"email": user["email"], "role": role.value},
    )
    return TokenResponse(access_token=token, role=role)


async def get_user_by_id(user_id: str):
    db = get_db()
    users = db["users"]
    try:
        oid = ObjectId(user_id)
    except Exception:
        return None
    return await users.find_one({"_id": oid})

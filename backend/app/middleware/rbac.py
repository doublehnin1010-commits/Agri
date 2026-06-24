from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import settings
from app.core.roles import ADMIN_ONLY_PATHS, ADMIN_ONLY_PREFIXES, Role
from app.core.security import decode_token


class RBACMiddleware(BaseHTTPMiddleware):
    """Block non-admin users from admin-only routes before handlers run."""

    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)

        path = request.url.path
        rbac_path = path.removeprefix(settings.api_v1_prefix) or "/"
        method = request.method.upper()

        is_admin_route = (method, rbac_path) in ADMIN_ONLY_PATHS or any(
            method == m and rbac_path.startswith(prefix) for m, prefix in ADMIN_ONLY_PREFIXES
        )
        if not is_admin_route:
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"detail": "Missing Authorization header"})

        token = auth_header.removeprefix("Bearer ").strip()
        try:
            payload = decode_token(token)
        except Exception:
            return JSONResponse(status_code=401, content={"detail": "Invalid token"})

        role = payload.get("role", Role.USER.value)
        if role != Role.ADMIN.value:
            return JSONResponse(status_code=403, content={"detail": "Admin access required"})

        return await call_next(request)

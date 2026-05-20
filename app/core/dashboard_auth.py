import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from app.config import get_settings

SESSION_COOKIE = "dashboard_session"
SESSION_TTL_SECONDS = 60 * 60 * 24 * 7


def _session_secret() -> bytes:
    settings = get_settings()
    secret = settings.dashboard_session_secret or settings.service_token
    return secret.encode("utf-8")


def create_session_token(username: str) -> str:
    payload = {
        "sub": username,
        "exp": int(time.time()) + SESSION_TTL_SECONDS,
    }
    payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(payload_bytes).decode("ascii").rstrip("=")
    signature = hmac.new(_session_secret(), payload_b64.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{signature}"


def verify_session_token(token: str | None) -> str | None:
    if not token or "." not in token:
        return None
    payload_b64, signature = token.split(".", 1)
    expected = hmac.new(_session_secret(), payload_b64.encode("ascii"), hashlib.sha256).hexdigest()
    if not secrets.compare_digest(signature, expected):
        return None
    padding = "=" * (-len(payload_b64) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(payload_b64 + padding))
    except (json.JSONDecodeError, ValueError):
        return None
    if payload.get("exp", 0) < int(time.time()):
        return None
    username = payload.get("sub")
    return username if isinstance(username, str) and username else None


def verify_dashboard_credentials(username: str, password: str) -> bool:
    settings = get_settings()
    return secrets.compare_digest(username, settings.dashboard_username) and secrets.compare_digest(
        password, settings.dashboard_password
    )


def get_session_username(request: Request) -> str | None:
    return verify_session_token(request.cookies.get(SESSION_COOKIE))


def require_dashboard_session(request: Request) -> str:
    username = get_session_username(request)
    if username is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="dashboard login required")
    return username


def _is_public_path(path: str, method: str) -> bool:
    if path in {"/login", "/health", "/health/ready", "/openapi.json", "/docs", "/redoc"}:
        return True
    if path.startswith("/docs") or path.startswith("/redoc"):
        return True
    if path in {"/auth/login", "/auth/logout"} and method == "POST":
        return True
    if path == "/bots/action" and method == "POST":
        return True
    return False


def _wants_json(request: Request) -> bool:
    accept = request.headers.get("accept", "")
    return "application/json" in accept or request.url.path.startswith("/bots") or request.url.path.startswith("/bot-")


class DashboardAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        if _is_public_path(path, request.method):
            return await call_next(request)

        if path.startswith("/static/"):
            return await call_next(request)

        if get_session_username(request) is not None:
            return await call_next(request)

        if _wants_json(request):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "dashboard login required"},
            )
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)


def set_session_cookie(response: Response, username: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=SESSION_COOKIE,
        value=create_session_token(username),
        httponly=True,
        samesite="lax",
        secure=settings.dashboard_cookie_secure,
        max_age=SESSION_TTL_SECONDS,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(key=SESSION_COOKIE, path="/", secure=settings.dashboard_cookie_secure)

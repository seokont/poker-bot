from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.core.dashboard_auth import (
    clear_session_cookie,
    get_session_username,
    set_session_cookie,
    verify_dashboard_credentials,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=256)


@router.post("/login")
def login(data: LoginRequest) -> JSONResponse:
    if not verify_dashboard_credentials(data.username, data.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid username or password")

    response = JSONResponse({"ok": True, "username": data.username})
    set_session_cookie(response, data.username)
    return response


@router.post("/logout")
def logout() -> JSONResponse:
    response = JSONResponse({"ok": True})
    clear_session_cookie(response)
    return response


@router.get("/me")
def current_user(request: Request) -> dict[str, str | bool]:
    username = get_session_username(request)
    if username is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not authenticated")
    return {"authenticated": True, "username": username}

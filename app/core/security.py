from fastapi import Header, HTTPException, status

from app.config import get_settings


def verify_service_token(authorization: str | None = Header(default=None)) -> None:
    expected = f"Bearer {get_settings().service_token}"
    if authorization != expected:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="invalid service token")

"""Signed session cookie helpers using itsdangerous."""

from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from fastapi import Request, Response

from config import SESSION_SECRET_KEY, SESSION_TIMEOUT_SECONDS

COOKIE_NAME = "vsnt_session"

_signer = URLSafeTimedSerializer(SESSION_SECRET_KEY, salt="vsnt-session")


def sign_session(data: dict) -> str:
    return _signer.dumps(data)


def verify_session(token: str, max_age: int | None = None) -> dict | None:
    """Return the payload dict or None if expired/invalid."""
    try:
        return _signer.loads(token, max_age=max_age or SESSION_TIMEOUT_SECONDS)
    except (BadSignature, SignatureExpired):
        return None


def set_session_cookie(response: Response, data: dict, timeout: int | None = None) -> None:
    token = sign_session(data)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=timeout or SESSION_TIMEOUT_SECONDS,
        httponly=True,
        samesite="lax",
        secure=False,  # localhost HTTP — no TLS needed per constitution
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=COOKIE_NAME, httponly=True, samesite="lax")


def get_session_data(request: Request, timeout: int | None = None) -> dict | None:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    return verify_session(token, max_age=timeout)

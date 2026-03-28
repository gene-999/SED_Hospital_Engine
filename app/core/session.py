"""
Lightweight cookie-based session for unauthenticated patients.

Stores:
  stage         : "looking" | "booking" | "booked"
  reservation_id: str | None
  hospital_id   : str | None
  ward_id       : str | None
  cancel_token  : str | None   — lets patient cancel without an account

The cookie value is a signed JWT so the server can trust its contents.
Cookie name: patient_session
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Cookie, Response
from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.config import settings

COOKIE_NAME = "patient_session"
COOKIE_MAX_AGE = 60 * 60 * 24  # 24 hours
ALGO = "HS256"


class PatientSession(BaseModel):
    stage: str = "looking"           # looking | booking | booked
    reservation_id: Optional[str] = None
    hospital_id: Optional[str] = None
    ward_id: Optional[str] = None
    cancel_token: Optional[str] = None


def _sign(data: dict) -> str:
    exp = datetime.now(timezone.utc) + timedelta(seconds=COOKIE_MAX_AGE)
    return jwt.encode({**data, "exp": exp}, settings.SECRET_KEY, algorithm=ALGO)


def _verify(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGO])
    except JWTError:
        return None


def read_session(patient_session: Optional[str] = Cookie(default=None)) -> PatientSession:
    """FastAPI dependency — reads and verifies the session cookie."""
    if not patient_session:
        return PatientSession()
    data = _verify(patient_session)
    if not data:
        return PatientSession()
    data.pop("exp", None)
    try:
        return PatientSession(**data)
    except Exception:
        return PatientSession()


def set_session(response: Response, session: PatientSession) -> None:
    """Write the session cookie onto a response."""
    token = _sign(session.model_dump())
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=False,  # set True behind HTTPS in production
    )


def clear_session(response: Response) -> None:
    response.delete_cookie(key=COOKIE_NAME)

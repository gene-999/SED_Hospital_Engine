from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from beanie import Document, Indexed
from pydantic import Field
from pymongo import IndexModel, ASCENDING


class UserRole(str, Enum):
    PATIENT = "PATIENT"
    HOSPITAL_ADMIN = "HOSPITAL_ADMIN"


class User(Document):
    name: str
    email: Indexed(str, unique=True)  # type: ignore[valid-type]
    password_hash: str
    role: UserRole
    phone: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "users"

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from beanie import Document, PydanticObjectId
from pydantic import Field
from pymongo import ASCENDING, IndexModel


class ReservationStatus(str, Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
    EXPIRED = "EXPIRED"
    CHECKED_IN = "CHECKED_IN"
    CANCELLED = "CANCELLED"


class Reservation(Document):
    # Patient identity — None for anonymous (unauthenticated) patients
    user_id: Optional[PydanticObjectId] = None
    patient_name: Optional[str] = None
    patient_phone: Optional[str] = None

    # Patient's location at time of reservation (for Mapbox ETA)
    patient_lat: Optional[float] = None
    patient_lng: Optional[float] = None

    # Hospital / ward / bed
    hospital_id: PydanticObjectId
    ward_id: PydanticObjectId
    bed_id: Optional[PydanticObjectId] = None

    status: ReservationStatus = ReservationStatus.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None

    # Token that allows unauthenticated patients to cancel their own reservation
    cancel_token: str = Field(default_factory=lambda: str(uuid.uuid4()))

    class Settings:
        name = "reservations"
        indexes = [
            IndexModel([("user_id", ASCENDING)]),
            IndexModel([("hospital_id", ASCENDING), ("status", ASCENDING)]),
            IndexModel([("status", ASCENDING), ("expires_at", ASCENDING)]),
        ]

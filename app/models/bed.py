from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from beanie import Document, PydanticObjectId
from pydantic import Field
from pymongo import ASCENDING, IndexModel


class BedStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    OCCUPIED = "OCCUPIED"


class Bed(Document):
    ward_id: PydanticObjectId
    hospital_id: PydanticObjectId  # denormalised for fast hospital-level queries
    status: BedStatus = BedStatus.AVAILABLE
    reservation_id: Optional[PydanticObjectId] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "beds"
        indexes = [
            IndexModel([("ward_id", ASCENDING), ("status", ASCENDING)]),
            IndexModel([("hospital_id", ASCENDING), ("status", ASCENDING)]),
        ]

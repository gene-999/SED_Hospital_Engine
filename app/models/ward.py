from datetime import datetime, timezone
from enum import Enum

from beanie import Document, PydanticObjectId
from pydantic import Field
from pymongo import ASCENDING, IndexModel


class WardType(str, Enum):
    ICU = "ICU"
    GENERAL = "GENERAL"
    MATERNITY = "MATERNITY"
    ER = "ER"


class Ward(Document):
    hospital_id: PydanticObjectId
    name: WardType
    total_beds: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "wards"
        indexes = [
            IndexModel([("hospital_id", ASCENDING)]),
        ]

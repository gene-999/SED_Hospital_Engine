from datetime import datetime, timezone
from typing import Optional, Any

from beanie import Document, PydanticObjectId
from pydantic import Field
from pymongo import ASCENDING, GEOSPHERE, IndexModel


class Hospital(Document):
    hospital_name: str
    admin_id: PydanticObjectId
    # GeoJSON Point — used for 2dsphere geospatial queries
    location: dict = Field(
        default_factory=lambda: {"type": "Point", "coordinates": [0.0, 0.0]}
    )
    address: str
    image_url: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    opening_hours: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def lat(self) -> float:
        return self.location["coordinates"][1]

    @property
    def lng(self) -> float:
        return self.location["coordinates"][0]

    @staticmethod
    def make_location(lat: float, lng: float) -> dict:
        return {"type": "Point", "coordinates": [lng, lat]}

    class Settings:
        name = "hospitals"
        indexes = [
            IndexModel([("location", GEOSPHERE)]),  # 2dsphere index for $near queries
            IndexModel([("admin_id", ASCENDING)]),
        ]

from typing import Optional
from pydantic import BaseModel
from app.models.bed import BedStatus


class BedOut(BaseModel):
    id: str
    ward_id: str
    hospital_id: str
    status: BedStatus
    reservation_id: Optional[str] = None


class BedStatusUpdate(BaseModel):
    status: BedStatus


class BedReassign(BaseModel):
    bed_id: str
    new_ward_id: str

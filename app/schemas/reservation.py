from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from app.models.reservation import ReservationStatus


class ReservationCreate(BaseModel):
    hospital_id: str
    ward_id: str
    # Patient contact — required for anonymous patients
    patient_name: Optional[str] = None
    patient_phone: Optional[str] = None
    # Patient's current location — used for Mapbox ETA on acceptance
    patient_lat: Optional[float] = None
    patient_lng: Optional[float] = None


class ReservationOut(BaseModel):
    id: str
    user_id: Optional[str] = None
    patient_name: Optional[str] = None
    patient_phone: Optional[str] = None
    hospital_id: str
    ward_id: str
    bed_id: Optional[str] = None
    status: ReservationStatus
    created_at: datetime
    expires_at: Optional[datetime] = None
    # Returned on creation so anonymous patients can cancel later
    cancel_token: str


class CancelRequest(BaseModel):
    cancel_token: str

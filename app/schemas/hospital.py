from typing import Any, Optional
from pydantic import BaseModel


class HospitalCreate(BaseModel):
    hospital_name: str
    lat: float
    lng: float
    address: str
    image_url: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    opening_hours: dict[str, Any] = {}


class HospitalUpdate(BaseModel):
    hospital_name: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    address: Optional[str] = None
    image_url: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    opening_hours: Optional[dict[str, Any]] = None


class HospitalOut(BaseModel):
    id: str
    hospital_name: str
    admin_id: str
    lat: float
    lng: float
    address: str
    image_url: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    opening_hours: dict[str, Any] = {}
    available_beds: int = 0
    wards: list[dict] = []

from typing import Optional
from pydantic import BaseModel
from app.models.ward import WardType


class SearchRequest(BaseModel):
    query: str
    user_lat: float  # required — search is location-first
    user_lng: float
    radius_km: Optional[float] = None  # overrides default if provided


class SearchFilters(BaseModel):
    ward_type: Optional[WardType] = None
    emergency: bool = False
    radius_km: float  # set from request or config default
    availability_required: bool = True


class HospitalSearchResult(BaseModel):
    id: str
    hospital_name: str
    address: str
    lat: float
    lng: float
    distance_km: float
    available_beds: int
    wards: list[dict] = []

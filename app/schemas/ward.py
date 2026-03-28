from typing import Optional
from pydantic import BaseModel
from app.models.ward import WardType


class WardCreate(BaseModel):
    hospital_id: str
    name: WardType
    number_of_beds: int


class WardUpdate(BaseModel):
    name: Optional[WardType] = None


class WardOut(BaseModel):
    id: str
    hospital_id: str
    name: WardType
    total_beds: int
    available_beds: int = 0

from fastapi import APIRouter, Depends, status

from app.core.deps import require_role
from app.models.user import User, UserRole
from app.schemas.hospital import HospitalCreate, HospitalUpdate, HospitalOut
from app.services import hospital as hospital_service

router = APIRouter(prefix="/hospitals", tags=["hospitals"])


@router.post("", response_model=HospitalOut, status_code=status.HTTP_201_CREATED)
async def create_hospital(
    data: HospitalCreate,
    admin: User = Depends(require_role(UserRole.HOSPITAL_ADMIN)),
) -> HospitalOut:
    return await hospital_service.create_hospital(data, admin)


@router.get("/{hospital_id}", response_model=HospitalOut)
async def get_hospital(hospital_id: str) -> HospitalOut:
    return await hospital_service.get_hospital(hospital_id)


@router.patch("/{hospital_id}", response_model=HospitalOut)
async def update_hospital(
    hospital_id: str,
    data: HospitalUpdate,
    admin: User = Depends(require_role(UserRole.HOSPITAL_ADMIN)),
) -> HospitalOut:
    return await hospital_service.update_hospital(hospital_id, data, admin)

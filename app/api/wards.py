from fastapi import APIRouter, Depends, status

from app.core.deps import require_role
from app.models.user import User, UserRole
from app.schemas.ward import WardCreate, WardUpdate, WardOut
from app.services import ward as ward_service

router = APIRouter(prefix="/wards", tags=["wards"])


@router.post("", response_model=WardOut, status_code=status.HTTP_201_CREATED)
async def create_ward(
    data: WardCreate,
    admin: User = Depends(require_role(UserRole.HOSPITAL_ADMIN)),
) -> WardOut:
    return await ward_service.create_ward(data, admin)


@router.get("/{ward_id}", response_model=WardOut)
async def get_ward(ward_id: str) -> WardOut:
    return await ward_service.get_ward(ward_id)


@router.patch("/{ward_id}", response_model=WardOut)
async def update_ward(
    ward_id: str,
    data: WardUpdate,
    admin: User = Depends(require_role(UserRole.HOSPITAL_ADMIN)),
) -> WardOut:
    return await ward_service.update_ward(ward_id, data, admin)


@router.delete("/{ward_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ward(
    ward_id: str,
    admin: User = Depends(require_role(UserRole.HOSPITAL_ADMIN)),
) -> None:
    await ward_service.delete_ward(ward_id, admin)

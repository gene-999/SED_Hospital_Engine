from fastapi import APIRouter, Depends, HTTPException, status

from app.core.deps import require_role
from app.models.bed import Bed, BedStatus
from app.models.hospital import Hospital
from app.models.user import User, UserRole
from app.models.ward import Ward
from app.schemas.bed import BedOut, BedStatusUpdate, BedReassign
from app.api.websocket import manager

router = APIRouter(prefix="/beds", tags=["beds"])


def _bed_out(bed: Bed) -> BedOut:
    return BedOut(
        id=str(bed.id),
        ward_id=str(bed.ward_id),
        hospital_id=str(bed.hospital_id),
        status=bed.status,
        reservation_id=str(bed.reservation_id) if bed.reservation_id else None,
    )


@router.patch("/{bed_id}", response_model=BedOut)
async def update_bed_status(
    bed_id: str,
    data: BedStatusUpdate,
    admin: User = Depends(require_role(UserRole.HOSPITAL_ADMIN)),
) -> BedOut:
    bed = await Bed.get(bed_id)
    if not bed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bed not found")

    hospital = await Hospital.get(bed.hospital_id)
    if not hospital or hospital.admin_id != admin.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not the hospital owner")

    await bed.set({Bed.status: data.status})
    await bed.sync()

    await manager.broadcast(
        f"ward:{str(bed.ward_id)}",
        {"event": "bed_status_changed", "bed_id": bed_id, "status": data.status},
    )
    return _bed_out(bed)


@router.post("/reassign", response_model=BedOut)
async def reassign_bed(
    data: BedReassign,
    admin: User = Depends(require_role(UserRole.HOSPITAL_ADMIN)),
) -> BedOut:
    bed = await Bed.get(data.bed_id)
    if not bed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bed not found")
    if bed.status != BedStatus.AVAILABLE:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Can only reassign available beds")

    new_ward = await Ward.get(data.new_ward_id)
    if not new_ward:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target ward not found")

    hospital = await Hospital.get(bed.hospital_id)
    if not hospital or hospital.admin_id != admin.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not the hospital owner")

    await bed.set({Bed.ward_id: new_ward.id})
    await bed.sync()
    return _bed_out(bed)

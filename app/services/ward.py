from fastapi import HTTPException, status

from app.models.bed import Bed, BedStatus
from app.models.hospital import Hospital
from app.models.ward import Ward
from app.models.user import User
from app.schemas.ward import WardCreate, WardUpdate, WardOut


async def create_ward(data: WardCreate, admin: User) -> WardOut:
    hospital = await Hospital.get(data.hospital_id)
    if not hospital:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hospital not found")
    if hospital.admin_id != admin.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not the hospital owner")

    ward = Ward(hospital_id=hospital.id, name=data.name, total_beds=data.number_of_beds)
    await ward.insert()

    # Auto-generate bed records
    beds = [Bed(ward_id=ward.id, hospital_id=hospital.id) for _ in range(data.number_of_beds)]
    if beds:
        await Bed.insert_many(beds)

    return await _to_out(ward)


async def get_ward(ward_id: str) -> WardOut:
    ward = await _get_or_404(ward_id)
    return await _to_out(ward)


async def update_ward(ward_id: str, data: WardUpdate, admin: User) -> WardOut:
    ward = await _get_or_404(ward_id)
    await _assert_owner(ward, admin)
    updates = data.model_dump(exclude_none=True)
    if updates:
        await ward.set(updates)
        await ward.sync()
    return await _to_out(ward)


async def delete_ward(ward_id: str, admin: User) -> None:
    ward = await _get_or_404(ward_id)
    await _assert_owner(ward, admin)

    occupied = await Bed.find(Bed.ward_id == ward.id, Bed.status == BedStatus.OCCUPIED).count()
    if occupied > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete ward with occupied beds",
        )

    await Bed.find(Bed.ward_id == ward.id).delete()
    await ward.delete()


async def _get_or_404(ward_id: str) -> Ward:
    ward = await Ward.get(ward_id)
    if not ward:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ward not found")
    return ward


async def _assert_owner(ward: Ward, admin: User) -> None:
    hospital = await Hospital.get(ward.hospital_id)
    if not hospital or hospital.admin_id != admin.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not the hospital owner")


async def _to_out(ward: Ward) -> WardOut:
    available_beds = await Bed.find(
        Bed.ward_id == ward.id, Bed.status == BedStatus.AVAILABLE
    ).count()
    return WardOut(
        id=str(ward.id),
        hospital_id=str(ward.hospital_id),
        name=ward.name,
        total_beds=ward.total_beds,
        available_beds=available_beds,
    )

from fastapi import HTTPException, status

from app.models.hospital import Hospital
from app.models.bed import Bed, BedStatus
from app.models.user import User
from app.schemas.hospital import HospitalCreate, HospitalUpdate, HospitalOut


async def create_hospital(data: HospitalCreate, admin: User) -> HospitalOut:
    existing = await Hospital.find_one(Hospital.admin_id == admin.id)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Admin already has a hospital")

    hospital = Hospital(
        hospital_name=data.hospital_name,
        admin_id=admin.id,
        location=Hospital.make_location(data.lat, data.lng),
        address=data.address,
        phone=data.phone,
        email=data.email,
        opening_hours=data.opening_hours,
    )
    await hospital.insert()
    return await _to_out(hospital)


async def get_hospital(hospital_id: str) -> HospitalOut:
    hospital = await _get_or_404(hospital_id)
    return await _to_out(hospital)


async def update_hospital(hospital_id: str, data: HospitalUpdate, admin: User) -> HospitalOut:
    hospital = await _get_or_404(hospital_id)
    _assert_owner(hospital, admin)

    updates = data.model_dump(exclude_none=True)

    # If lat/lng are being updated, rebuild the GeoJSON location field
    lat = updates.pop("lat", None)
    lng = updates.pop("lng", None)
    if lat is not None or lng is not None:
        new_lat = lat if lat is not None else hospital.lat
        new_lng = lng if lng is not None else hospital.lng
        updates["location"] = Hospital.make_location(new_lat, new_lng)

    if updates:
        await hospital.set(updates)
        await hospital.sync()
    return await _to_out(hospital)


async def _get_or_404(hospital_id: str) -> Hospital:
    hospital = await Hospital.get(hospital_id)
    if not hospital:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hospital not found")
    return hospital


def _assert_owner(hospital: Hospital, admin: User) -> None:
    if hospital.admin_id != admin.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not the hospital owner")


async def _to_out(hospital: Hospital) -> HospitalOut:
    available_beds = await Bed.find(
        Bed.hospital_id == hospital.id,
        Bed.status == BedStatus.AVAILABLE,
    ).count()
    return HospitalOut(
        id=str(hospital.id),
        hospital_name=hospital.hospital_name,
        admin_id=str(hospital.admin_id),
        lat=hospital.lat,
        lng=hospital.lng,
        address=hospital.address,
        phone=hospital.phone,
        email=hospital.email,
        opening_hours=hospital.opening_hours,
        available_beds=available_beds,
    )

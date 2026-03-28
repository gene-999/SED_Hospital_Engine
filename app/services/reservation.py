from datetime import datetime, timedelta, timezone
from typing import Optional

from bson import ObjectId
from fastapi import HTTPException, status

from app.core.config import settings
from app.models.bed import Bed, BedStatus
from app.models.hospital import Hospital
from app.models.reservation import Reservation, ReservationStatus
from app.models.ward import Ward
from app.models.user import User
from app.schemas.reservation import ReservationCreate, ReservationOut
from app.services.mapbox import get_driving_duration_seconds
from app.api.websocket import manager


async def create_reservation(
    data: ReservationCreate,
    current_user: Optional[User],
) -> ReservationOut:
    hospital = await Hospital.get(data.hospital_id)
    if not hospital:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hospital not found")

    ward = await Ward.get(data.ward_id)
    if not ward or str(ward.hospital_id) != data.hospital_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ward not found in hospital")

    reservation = Reservation(
        user_id=current_user.id if current_user else None,
        patient_name=data.patient_name or (current_user.name if current_user else None),
        patient_phone=data.patient_phone or (current_user.phone if current_user else None),
        patient_lat=data.patient_lat,
        patient_lng=data.patient_lng,
        hospital_id=hospital.id,
        ward_id=ward.id,
    )
    await reservation.insert()

    await manager.broadcast(
        f"hospital:{data.hospital_id}",
        {"event": "new_reservation", "reservation_id": str(reservation.id)},
    )
    return _to_out(reservation)


async def accept_reservation(reservation_id: str, admin: User) -> ReservationOut:
    reservation = await _get_or_404(reservation_id)
    await _assert_hospital_admin(reservation, admin)

    if reservation.status != ReservationStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Reservation is not pending")

    # Atomic bed assignment — prevents double booking
    collection = Bed.get_pymongo_collection()
    result = await collection.find_one_and_update(
        {
            "ward_id": ObjectId(str(reservation.ward_id)),
            "status": BedStatus.AVAILABLE,
        },
        {
            "$set": {
                "status": BedStatus.RESERVED,
                "reservation_id": ObjectId(str(reservation.id)),
            }
        },
        sort=[("created_at", 1)],
        return_document=True,
    )

    if result is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No available beds in this ward")

    bed_id = result["_id"]
    hospital = await Hospital.get(reservation.hospital_id)

    # Compute ETA-based expiry using Mapbox
    expires_at = await _compute_expiry(reservation, hospital)

    await reservation.set(
        {
            Reservation.status: ReservationStatus.ACCEPTED,
            Reservation.bed_id: bed_id,
            Reservation.expires_at: expires_at,
        }
    )
    await reservation.sync()

    await manager.broadcast(
        f"hospital:{str(reservation.hospital_id)}",
        {
            "event": "reservation_accepted",
            "reservation_id": reservation_id,
            "bed_id": str(bed_id),
            "expires_at": expires_at.isoformat(),
        },
    )
    await manager.broadcast(
        f"ward:{str(reservation.ward_id)}",
        {"event": "bed_reserved", "bed_id": str(bed_id)},
    )
    return _to_out(reservation)


async def decline_reservation(reservation_id: str, admin: User) -> ReservationOut:
    reservation = await _get_or_404(reservation_id)
    await _assert_hospital_admin(reservation, admin)

    if reservation.status != ReservationStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Reservation is not pending")

    await reservation.set({Reservation.status: ReservationStatus.DECLINED})
    await reservation.sync()
    return _to_out(reservation)


async def checkin_reservation(reservation_id: str, admin: User) -> ReservationOut:
    reservation = await _get_or_404(reservation_id)
    await _assert_hospital_admin(reservation, admin)

    if reservation.status != ReservationStatus.ACCEPTED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Reservation is not accepted")

    await reservation.set({Reservation.status: ReservationStatus.CHECKED_IN})
    await reservation.sync()

    if reservation.bed_id:
        bed = await Bed.get(reservation.bed_id)
        if bed:
            await bed.set({Bed.status: BedStatus.OCCUPIED})
            await manager.broadcast(
                f"ward:{str(reservation.ward_id)}",
                {"event": "bed_occupied", "bed_id": str(reservation.bed_id)},
            )

    return _to_out(reservation)


async def cancel_reservation(
    reservation_id: str,
    cancel_token: str,
    current_user: Optional[User],
) -> ReservationOut:
    reservation = await _get_or_404(reservation_id)

    # Allow cancellation if: authenticated owner OR correct cancel_token
    is_owner = current_user and str(reservation.user_id) == str(current_user.id)
    has_token = reservation.cancel_token == cancel_token

    if not is_owner and not has_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorised to cancel this reservation",
        )

    if reservation.status not in (ReservationStatus.PENDING, ReservationStatus.ACCEPTED):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot cancel at this stage")

    if reservation.bed_id and reservation.status == ReservationStatus.ACCEPTED:
        bed = await Bed.get(reservation.bed_id)
        if bed:
            await bed.set({Bed.status: BedStatus.AVAILABLE, Bed.reservation_id: None})
            await manager.broadcast(
                f"ward:{str(reservation.ward_id)}",
                {"event": "bed_available", "bed_id": str(reservation.bed_id)},
            )

    await reservation.set({Reservation.status: ReservationStatus.CANCELLED})
    await reservation.sync()
    return _to_out(reservation)


async def _compute_expiry(reservation: Reservation, hospital: Optional[Hospital]) -> datetime:
    """
    Query Mapbox for driving duration from patient to hospital.
    expires_at = now + drive_duration + EXPIRY_BUFFER_MINUTES.
    Falls back to EXPIRY_FALLBACK_MINUTES if Mapbox is unavailable.
    """
    now = datetime.now(timezone.utc)
    buffer = timedelta(minutes=settings.EXPIRY_BUFFER_MINUTES)

    if (
        reservation.patient_lat is not None
        and reservation.patient_lng is not None
        and hospital is not None
    ):
        duration_seconds = await get_driving_duration_seconds(
            from_lat=reservation.patient_lat,
            from_lng=reservation.patient_lng,
            to_lat=hospital.lat,
            to_lng=hospital.lng,
        )
        if duration_seconds is not None:
            return now + timedelta(seconds=duration_seconds) + buffer

    # Fallback
    return now + timedelta(minutes=settings.EXPIRY_FALLBACK_MINUTES)


async def _get_or_404(reservation_id: str) -> Reservation:
    reservation = await Reservation.get(reservation_id)
    if not reservation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")
    return reservation


async def _assert_hospital_admin(reservation: Reservation, admin: User) -> None:
    hospital = await Hospital.get(reservation.hospital_id)
    if not hospital or hospital.admin_id != admin.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not the hospital owner")


def _to_out(reservation: Reservation) -> ReservationOut:
    return ReservationOut(
        id=str(reservation.id),
        user_id=str(reservation.user_id) if reservation.user_id else None,
        patient_name=reservation.patient_name,
        patient_phone=reservation.patient_phone,
        hospital_id=str(reservation.hospital_id),
        ward_id=str(reservation.ward_id),
        bed_id=str(reservation.bed_id) if reservation.bed_id else None,
        status=reservation.status,
        created_at=reservation.created_at,
        expires_at=reservation.expires_at,
        cancel_token=reservation.cancel_token,
    )

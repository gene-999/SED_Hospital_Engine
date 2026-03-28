"""
Background job that expires accepted reservations whose 40-minute window has passed.
Runs every minute via APScheduler.
"""
from datetime import datetime, timezone

from app.models.bed import Bed, BedStatus
from app.models.reservation import Reservation, ReservationStatus
from app.api.websocket import manager


async def expire_reservations() -> None:
    now = datetime.now(timezone.utc)

    expired = await Reservation.find(
        Reservation.status == ReservationStatus.ACCEPTED,
        Reservation.expires_at <= now,
    ).to_list()

    for reservation in expired:
        await reservation.set({Reservation.status: ReservationStatus.EXPIRED})

        if reservation.bed_id:
            bed = await Bed.get(reservation.bed_id)
            if bed and bed.status == BedStatus.RESERVED:
                await bed.set({Bed.status: BedStatus.AVAILABLE, Bed.reservation_id: None})
                await manager.broadcast(
                    f"ward:{str(reservation.ward_id)}",
                    {"event": "bed_available", "bed_id": str(reservation.bed_id)},
                )

        await manager.broadcast(
            f"hospital:{str(reservation.hospital_id)}",
            {"event": "reservation_expired", "reservation_id": str(reservation.id)},
        )

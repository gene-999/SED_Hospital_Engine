from typing import Optional

from fastapi import APIRouter, Depends, status

from app.core.deps import get_optional_user, require_role
from app.models.user import User, UserRole
from app.schemas.reservation import ReservationCreate, ReservationOut, CancelRequest
from app.services import reservation as reservation_service

router = APIRouter(prefix="/reservations", tags=["reservations"])


@router.post("", response_model=ReservationOut, status_code=status.HTTP_201_CREATED)
async def create_reservation(
    data: ReservationCreate,
    current_user: Optional[User] = Depends(get_optional_user),
) -> ReservationOut:
    """Anyone can make a reservation — no account required."""
    return await reservation_service.create_reservation(data, current_user)


@router.patch("/{reservation_id}/accept", response_model=ReservationOut)
async def accept_reservation(
    reservation_id: str,
    admin: User = Depends(require_role(UserRole.HOSPITAL_ADMIN)),
) -> ReservationOut:
    return await reservation_service.accept_reservation(reservation_id, admin)


@router.patch("/{reservation_id}/decline", response_model=ReservationOut)
async def decline_reservation(
    reservation_id: str,
    admin: User = Depends(require_role(UserRole.HOSPITAL_ADMIN)),
) -> ReservationOut:
    return await reservation_service.decline_reservation(reservation_id, admin)


@router.patch("/{reservation_id}/checkin", response_model=ReservationOut)
async def checkin_reservation(
    reservation_id: str,
    admin: User = Depends(require_role(UserRole.HOSPITAL_ADMIN)),
) -> ReservationOut:
    return await reservation_service.checkin_reservation(reservation_id, admin)


@router.patch("/{reservation_id}/cancel", response_model=ReservationOut)
async def cancel_reservation(
    reservation_id: str,
    data: CancelRequest,
    current_user: Optional[User] = Depends(get_optional_user),
) -> ReservationOut:
    """Cancel using either auth token (if logged in) or the cancel_token from creation."""
    return await reservation_service.cancel_reservation(
        reservation_id, data.cancel_token, current_user
    )

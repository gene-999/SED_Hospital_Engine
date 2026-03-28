from typing import Optional

from fastapi import APIRouter, Depends, Response, status

from app.core.deps import get_optional_user, require_role
from app.core.session import PatientSession, read_session, set_session, clear_session
from app.models.user import User, UserRole
from app.schemas.reservation import ReservationCreate, ReservationOut, CancelRequest
from app.services import reservation as reservation_service

router = APIRouter(prefix="/reservations", tags=["reservations"])


@router.post("", response_model=ReservationOut, status_code=status.HTTP_201_CREATED)
async def create_reservation(
    data: ReservationCreate,
    response: Response,
    current_user: Optional[User] = Depends(get_optional_user),
    session: PatientSession = Depends(read_session),
) -> ReservationOut:
    """No authentication required — anyone can reserve a bed."""
    out = await reservation_service.create_reservation(data, current_user)

    session.stage = "booking"
    session.reservation_id = out.id
    session.hospital_id = out.hospital_id
    session.ward_id = out.ward_id
    session.cancel_token = out.cancel_token
    set_session(response, session)

    return out


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
    response: Response,
    current_user: Optional[User] = Depends(get_optional_user),
) -> ReservationOut:
    out = await reservation_service.cancel_reservation(
        reservation_id, data.cancel_token, current_user
    )
    clear_session(response)
    return out


@router.get("/session", response_model=PatientSession)
async def get_session(session: PatientSession = Depends(read_session)) -> PatientSession:
    """Returns the current patient session state from the cookie."""
    return session


@router.get("/{reservation_id}/status", response_model=ReservationOut)
async def get_reservation_status(reservation_id: str) -> ReservationOut:
    """Polls the current status of a reservation."""
    return await reservation_service.get_reservation(reservation_id)

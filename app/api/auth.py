from fastapi import APIRouter, Depends, status

from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.user import SignupRequest, LoginRequest, TokenResponse, RefreshRequest, UserOut
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(data: SignupRequest) -> TokenResponse:
    return await auth_service.signup(data)


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest) -> TokenResponse:
    return await auth_service.login(data)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest) -> TokenResponse:
    return await auth_service.refresh(data.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(data: RefreshRequest) -> None:
    await auth_service.logout(data.refresh_token)


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut(id=str(user.id), name=user.name, email=user.email, role=user.role, phone=user.phone)

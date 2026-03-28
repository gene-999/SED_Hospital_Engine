from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from jose import JWTError

from app.core.config import settings
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from app.models.user import User, UserRole
from app.models.refresh_token import RefreshToken
from app.schemas.user import SignupRequest, LoginRequest, TokenResponse


async def signup(data: SignupRequest) -> TokenResponse:
    existing = await User.find_one(User.email == data.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        role=data.role,
        phone=data.phone,
    )
    await user.insert()
    return await _issue_tokens(user)


async def login(data: LoginRequest) -> TokenResponse:
    user = await User.find_one(User.email == data.email)
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    return await _issue_tokens(user)


async def refresh(refresh_token_str: str) -> TokenResponse:
    try:
        payload = decode_token(refresh_token_str)
        if payload.get("type") != "refresh":
            raise ValueError
        user_id = payload["sub"]
    except (JWTError, ValueError, KeyError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    stored = await RefreshToken.find_one(
        RefreshToken.token == refresh_token_str,
        RefreshToken.revoked == False,
    )
    if not stored or stored.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired or revoked")

    await stored.set({RefreshToken.revoked: True})

    user = await User.get(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return await _issue_tokens(user)


async def logout(refresh_token_str: str) -> None:
    stored = await RefreshToken.find_one(RefreshToken.token == refresh_token_str)
    if stored:
        await stored.set({RefreshToken.revoked: True})


async def _issue_tokens(user: User) -> TokenResponse:
    access = create_access_token(str(user.id))
    refresh = create_refresh_token(str(user.id))

    rt = RefreshToken(
        user_id=user.id,
        token=refresh,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    await rt.insert()

    return TokenResponse(access_token=access, refresh_token=refresh)

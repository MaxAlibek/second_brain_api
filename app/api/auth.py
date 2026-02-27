from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.schemas.user import UserCreate, UserLogin
from app.services.user_service import create_user, get_user_by_username, verify_password
from app.db.session import get_db
from app.db.models.refresh_token import RefreshToken
from app.core.security import create_access_token, create_refresh_token
from app.core.config import settings
from jose import jwt, JWTError


router = APIRouter()


@router.post("/register")
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await get_user_by_username(db, user.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    new_user = await create_user(db, user.username, user.email, user.password)
    return new_user


@router.post("/login")
async def login(user: UserLogin, db: AsyncSession = Depends(get_db)):
    db_user = await get_user_by_username(db, user.username)

    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    access_token = create_access_token(db_user.id)
    refresh_token = create_refresh_token(db_user.id)

    # сохраняем refresh токен в БД
    db_token = RefreshToken(token=refresh_token, user_id=db_user.id)
    db.add(db_token)
    await db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/refresh")
async def refresh(refresh_token: str, db: AsyncSession = Depends(get_db)):
    try:
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        user_id = int(payload.get("sub"))

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    # проверяем что токен есть в БД
    result = await db.execute(select(RefreshToken).where(RefreshToken.token == refresh_token))
    db_token = result.scalar_one_or_none()

    if not db_token:
        raise HTTPException(status_code=401, detail="Token expired or revoked")

    new_access_token = create_access_token(user_id)

    return {"access_token": new_access_token}


@router.post("/logout")
async def logout(refresh_token: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RefreshToken).where(RefreshToken.token == refresh_token))
    db_token = result.scalar_one_or_none()

    if db_token:
        await db.delete(db_token)
        await db.commit()

    return {"message": "Logged out successfully"}
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.schemas.user import UserCreate, UserLogin
from app.services.user_service import create_user, get_user_by_username, get_user_by_email, verify_password
from app.db.database import get_db
from app.db.models import RefreshToken
from app.core.security import create_access_token, create_refresh_token
from app.core.config import settings
from jose import jwt, JWTError


router = APIRouter()


@router.post("/register")
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
    existing_username = await get_user_by_username(db, user.username)
    if existing_username:
        raise HTTPException(status_code=400, detail="Username already exists")
        
    existing_email = await get_user_by_email(db, user.email)
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = await create_user(db, user.username, user.email, user.password)
    return new_user


from fastapi.security import OAuth2PasswordRequestForm

@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    db_user = await get_user_by_username(db, form_data.username)

    if not db_user or not verify_password(form_data.password, db_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    access_token = create_access_token(db_user.id)
    refresh_token = create_refresh_token(db_user.id)

    # Высчитываем дату истечения, чтобы сохранить в БД
    from datetime import datetime, timedelta
    expire_date = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    # сохраняем refresh токен в БД
    db_token = RefreshToken(token=refresh_token, expires_at=expire_date, user_id=db_user.id)
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

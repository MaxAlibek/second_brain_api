from pydantic import BaseModel, EmailStr
from typing import Optional


# ==========================================================
# USER RESPONSE MODEL
# ==========================================================
class UserOut(BaseModel):
    """
    Схема, которая возвращается клиенту.
    Пароль никогда не отправляем наружу.
    """

    id: int
    username: str
    email: EmailStr
    is_active: bool

    class Config:
        from_attributes = True  # для SQLAlchemy (в новых версиях вместо orm_mode)


# ==========================================================
# USER REGISTRATION
# ==========================================================
class UserCreate(BaseModel):
    """
    Схема для регистрации.
    Принимаем обычный пароль,
    но в базе сохраняем уже хеш.
    """

    username: str
    email: EmailStr
    password: str


# ==========================================================
# USER LOGIN
# ==========================================================
class UserLogin(BaseModel):
    """
    Схема для логина.
    """

    username: str
    password: str


# ==========================================================
# ACCESS + REFRESH TOKENS RESPONSE
# ==========================================================
class Token(BaseModel):
    """
    То, что возвращаем после логина.
    """

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# ==========================================================
# TOKEN DATA (внутреннее использование)
# ==========================================================
class TokenData(BaseModel):
    """
    Используется внутри security слоя
    после декодирования JWT.
    """

    user_id: Optional[int] = None
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import User

# Настройка хеширования пароля
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Хешируем пароль
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

# Проверяем пароль
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# Создание нового пользователя
async def create_user(db: AsyncSession, username: str, email: str, password: str) -> User:
    hashed = hash_password(password)
    new_user = User(username=username, email=email, hashed_password=hashed)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)  # обновляем объект из базы, чтобы получить id
    return new_user

# Получение пользователя по username
async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()

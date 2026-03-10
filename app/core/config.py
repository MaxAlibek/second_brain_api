"""
Центральный конфиг всего приложения.
Все настройки подтягиваются из переменных окружения (или файла .env).
Pydantic автоматически валидирует типы и подставляет дефолтные значения.
Если чего-то не хватает (например, SECRET_KEY), приложение просто не запустится — и правильно.
"""

from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    # ---------------------------------------------------------------------------
    # База данных (PostgreSQL)
    # ---------------------------------------------------------------------------
    # Если DATABASE_URL задан целиком (как в Docker), берем его.
    # Если нет — собираем из отдельных кусочков (для локальной разработки).
    DATABASE_URL: Optional[str] = None
    POSTGRES_USER: str = "second_brain_user"
    POSTGRES_PASSWORD: str = "supersecret"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: str = "5432"
    POSTGRES_DB: str = "second_brain"

    # ---------------------------------------------------------------------------
    # Авторизация (JWT)
    # ---------------------------------------------------------------------------
    SECRET_KEY: str  # Обязательное поле! Без него ничего не работает.
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # Access-токен живет 1 час
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # Refresh-токен живет неделю
    
    # ---------------------------------------------------------------------------
    # ИИ Агент (Фаза 4)
    # ---------------------------------------------------------------------------
    GEMINI_API_KEY: Optional[str] = None  # Ключ от Google AI Studio (https://aistudio.google.com/)
    REDIS_URL: Optional[str] = "redis://localhost:6379/0"  # Брокер для Celery

    @property
    def get_database_url(self) -> str:
        """Умный геттер: если DATABASE_URL задан — вернет его, если нет — соберет из кусочков."""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    class Config:
        env_file = ".env"
        case_sensitive = False


# Синглтон настроек. Импортируй settings откуда угодно — это всегда один и тот же объект.
settings = Settings()

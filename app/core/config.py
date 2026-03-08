from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Если DATABASE_URL передан напрямую через переменные окружения, берем его.
    # Если нет, собираем его из отдельных переменных.
    DATABASE_URL: Optional[str] = None
    POSTGRES_USER: str = "second_brain_user"
    POSTGRES_PASSWORD: str = "supersecret"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: str = "5432"
    POSTGRES_DB: str = "second_brain"

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    @property
    def get_database_url(self) -> str:
        """Динамически собирает URL базы данных, если он не задан явно."""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

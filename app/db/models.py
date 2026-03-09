# app/db/models.py

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.database import Base


# ==========================================================
# USER MODEL
# ==========================================================
class User(Base):
    """
    Основная таблица пользователей.

    Один пользователь может:
    - иметь несколько refresh токенов
    - иметь несколько Brain записей
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)

    hashed_password = Column(String, nullable=False)

    is_active = Column(Boolean, default=True)

    # -----------------------------
    # Связь: Один User → много RefreshToken
    # -----------------------------
    refresh_tokens = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    # -----------------------------
    # Связь: Один User → много BrainEntry
    # -----------------------------
    brain_entries = relationship(
        "BrainEntry",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    # -----------------------------
    # Связь: Один User → много Tag
    # -----------------------------
    tags = relationship(
        "Tag",
        back_populates="user",
        cascade="all, delete-orphan"
    )


# ==========================================================
# REFRESH TOKEN MODEL
# ==========================================================
class RefreshToken(Base):
    """
    Таблица для хранения refresh токенов.

    Нужна для:
    - ротации токенов
    - logout
    - контроля устройств
    """

    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)

    token = Column(String, unique=True, nullable=False)

    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # связь обратно к пользователю
    user = relationship("User", back_populates="refresh_tokens")


# ==========================================================
# BRAIN ENTRY MODEL
# ==========================================================
class BrainEntry(Base):
    """
    Основная сущность Second Brain.

    Каждая запись принадлежит одному пользователю.
    """

    __tablename__ = "brain_entries"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String, nullable=True)
    content = Column(Text, nullable=False)

    category = Column(String, nullable=True)
    summary = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # связь обратно к пользователю
    user = relationship("User", back_populates="brain_entries")

    # связь многие-ко-многим с тегами
    tags = relationship("Tag", secondary="brain_entry_tags", back_populates="brain_entries")


# ==========================================================
# ASSOCIATION TABLE (Многие-ко-многим)
# ==========================================================
class BrainEntryTag(Base):
    """
    Промежуточная таблица-посредник для связи Заметок и Тегов.
    """

    __tablename__ = "brain_entry_tags"

    brain_entry_id = Column(Integer, ForeignKey("brain_entries.id", ondelete="CASCADE"), primary_key=True)
    tag_id = Column(Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ==========================================================
# TAG MODEL
# ==========================================================
class Tag(Base):
    """
    Модель Тега.
    """

    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), index=True, nullable=False)
    
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    __table_args__ = (
        UniqueConstraint('user_id', 'name', name='_user_tag_uc'),
    )

    user = relationship("User", back_populates="tags")
    brain_entries = relationship("BrainEntry", secondary="brain_entry_tags", back_populates="tags")
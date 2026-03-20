import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="user")  # user | admin
    credits: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    agent_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=10)  # -1 = unlimited
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_blocked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

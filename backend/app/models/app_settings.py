from sqlalchemy import String, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AppSettings(Base):
    __tablename__ = "app_settings"

    id: Mapped[str] = mapped_column(String(50), primary_key=True, default="default")
    allowed_models_json: Mapped[str] = mapped_column(Text, nullable=False)
    available_models_json: Mapped[str] = mapped_column(Text, nullable=False)
    credits_per_process: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    default_api_keys_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")

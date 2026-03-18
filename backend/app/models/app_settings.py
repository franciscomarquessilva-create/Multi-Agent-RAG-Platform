from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AppSettings(Base):
    __tablename__ = "app_settings"

    id: Mapped[str] = mapped_column(String(50), primary_key=True, default="default")
    allowed_models_json: Mapped[str] = mapped_column(Text, nullable=False)
    available_models_json: Mapped[str] = mapped_column(Text, nullable=False)

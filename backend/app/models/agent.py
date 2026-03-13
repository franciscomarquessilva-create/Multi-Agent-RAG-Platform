import uuid
import json
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    api_key_encrypted: Mapped[str] = mapped_column(String(500), nullable=False)
    agent_type: Mapped[str] = mapped_column(String(20), default="slave", nullable=False)
    purpose: Mapped[str] = mapped_column(Text, default="", nullable=False)
    instructions: Mapped[str] = mapped_column(Text, default="", nullable=False)
    orchestrator_mode: Mapped[str] = mapped_column(String(20), default="orchestrate", nullable=False)
    allowed_slave_ids_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    orchestration_rules_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    is_orchestrator: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    @property
    def allowed_slave_ids(self) -> list[str]:
        return json.loads(self.allowed_slave_ids_json or "[]")

    @allowed_slave_ids.setter
    def allowed_slave_ids(self, value: list[str]):
        self.allowed_slave_ids_json = json.dumps(value or [])

    @property
    def orchestration_rules(self) -> list[dict]:
        return json.loads(self.orchestration_rules_json or "[]")

    @orchestration_rules.setter
    def orchestration_rules(self, value: list[dict]):
        self.orchestration_rules_json = json.dumps(value or [])

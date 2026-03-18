from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    secret_key: str = ""
    database_url: str = "sqlite+aiosqlite:///./data/app.db"
    chroma_persist_dir: str = "./data/chroma"
    backend_cors_origins: str = "http://localhost:3000,http://localhost:5173"

    # Auth / access control
    cf_team_domain: str = ""           # e.g. "aiops3000" — set in prod to enable CF JWT validation
    admin_emails: str = ""             # comma-separated admin email list
    dev_user_email: str = ""           # local-dev fallback user email

    # Credits & limits
    default_user_credits: int = 100
    default_agent_limit: int = 10      # max agents per user (-1 = unlimited)
    credits_per_iteration: int = 1     # credits consumed per chat iteration

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.backend_cors_origins.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()

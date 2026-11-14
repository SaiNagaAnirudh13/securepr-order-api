import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_path: str = "./securepr_sample.sqlite3"
    session_ttl_seconds: int = 3600
    log_level: str = "INFO"

    @classmethod
    def from_environment(cls) -> "Settings":
        settings = cls(
            database_path=os.getenv("DATABASE_PATH", cls.database_path),
            session_ttl_seconds=int(os.getenv("SESSION_TTL_SECONDS", "3600")),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        )
        if settings.session_ttl_seconds <= 0:
            raise ValueError("SESSION_TTL_SECONDS must be positive")
        if settings.log_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("LOG_LEVEL must be a standard logging level")
        return settings

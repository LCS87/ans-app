"""Configurações da aplicação."""
from functools import lru_cache
from pathlib import Path
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import warnings


class Settings(BaseSettings):
    """Configurações carregadas de .env"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # API
    app_name: str = "ANS Intelligence API"
    app_version: str = "1.0.0"
    api_prefix: str = "/api/v1"
    debug: bool = False
    
    # CORS
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:8080",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8080"
    ]
    
    # Database (MySQL)
    mysql_host: str = "localhost"
    mysql_port: int = 3307
    mysql_user: str = "user"
    mysql_password: str = "password"
    mysql_database: str = "ans_db"
    
    @property
    def database_url(self) -> str:
        """URL SQLAlchemy para MySQL."""
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
        )
    
    # Cache (Redis)
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    cache_ttl: int = 300
    
    @property
    def redis_url(self) -> str:
        """URL Redis."""
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    # Paths
    project_root: Path = Path(__file__).parent.parent
    cadop_csv_path: Path = Path("etl/data/raw/operadoras_ativas/relatorio_cadop.csv")
    
    @property
    def cadop_csv_absolute(self) -> Path:
        """Caminho absoluto do CSV."""
        return self.project_root / self.cadop_csv_path
    
    # Security
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    @field_validator('secret_key')
    @classmethod
    def warn_default_secret(cls, v: str) -> str:
        if v in ("change-me-in-production", ""):
            warnings.warn("⚠️ SECRET_KEY insegura! Defina no .env")
        return v
    
    # Rate Limiting
    rate_limit_per_minute: int = 60
    
    # Notifications
    discord_webhook_url: str = ""
    
    # Scheduler
    scheduler_enabled: bool = True
    scheduler_timezone: str = "America/Sao_Paulo"


@lru_cache()
def get_settings() -> Settings:
    """Singleton de configurações."""
    return Settings()
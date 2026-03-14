"""Configurações da aplicação."""
import os
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configurações da aplicação carregadas de variáveis de ambiente."""
    
    # API
    app_name: str = "ANS Intelligence API"
    app_version: str = "1.0.0"
    api_prefix: str = "/api/v1"
    debug: bool = False
    
    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:8080"]
    
    # Database
    database_url: str = "mysql+mysqlconnector://user:password@localhost:3307/ans_db"
    
    # Cache
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl: int = 300  # 5 minutos
    
    # Search
    cadop_csv_path: str = "etl/data/raw/operadoras_ativas/relatorio_cadop.csv"
    
    # Security
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Rate Limiting
    rate_limit_per_minute: int = 60
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Retorna instância singleton das configurações."""
    return Settings()

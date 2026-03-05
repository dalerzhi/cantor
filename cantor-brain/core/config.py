"""
应用配置
使用 pydantic-settings 管理环境变量
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "Cantor Brain"
    VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/cantor"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT Configuration
    JWT_SECRET_KEY: str = "your-super-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Password
    PASSWORD_MIN_LENGTH: int = 12
    PASSWORD_HASH_COST: int = 12
    MAX_FAILED_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_DURATION_MINUTES: int = 30

    # API Key
    API_KEY_PREFIX: str = "cantor_"
    API_KEY_LENGTH: int = 48

    # CORS
    CORS_ORIGINS: str = "*"

    # IaaS Configuration
    IAAS_BASE_URL: str = "https://castack-gncenter.cheersucloud.com/openapi"
    IAAS_ACCESS_KEY: str = ""
    IAAS_SECRET_KEY: str = ""

    # RTC Signaling Backend Configuration
    SIGNALING_BASE_URL: str = "https://castack-signaling.cheersucloud.com"
    SIGNALING_ACCESS_KEY: str = ""
    SIGNALING_SECRET_KEY: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

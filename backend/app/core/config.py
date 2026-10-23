import os
from functools import lru_cache
from typing import List, Optional, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application Info
    PROJECT_NAME: str = "PromptForge AI"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # Server Binding
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000

    # CORS Configuration
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Database Configuration (PostgreSQL 16)
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "promptforge_user"
    POSTGRES_PASSWORD: str = "promptforge_secure_dev_password"
    POSTGRES_DB: str = "promptforge_db"
    DATABASE_URL: Optional[str] = None
    DB_POOL_TIMEOUT_SECONDS: float = 2.0

    @property
    def sync_database_uri(self) -> str:
        if self.DATABASE_URL:
            # Normalize to sync driver if needed
            return self.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def async_database_uri(self) -> str:
        if self.DATABASE_URL:
            if not self.DATABASE_URL.startswith("postgresql+asyncpg://"):
                return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
            return self.DATABASE_URL
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Local AI Inference Runtime Configuration (Local-first, provider-independent)
    AI_RUNTIME_BASE_URL: str = "http://localhost:11434"
    AI_RUNTIME_TIMEOUT_SECONDS: float = 3.0
    AI_CODE_MODEL_NAME: str = "qwen2.5-coder:1.5b"
    AI_CLASSIFIER_MODEL_NAME: str = "prompt-classifier-v1"

    # Model Artifacts Directory (File-system checkpoints)
    AI_MODELS_DIR: str = "./ai/models"

    # Execution Sandbox Configuration (Docker-based execution isolation)
    SANDBOX_ENABLED: bool = False
    SANDBOX_TIMEOUT_SECONDS: int = 15
    SANDBOX_MAX_MEMORY_MB: int = 512
    SANDBOX_NETWORK_ACCESS: bool = False
    DOCKER_PYTHON_IMAGE: str = "python:3.11-slim"

    # Code Ingestion and Verification Limits
    MAX_UPLOAD_SIZE_BYTES: int = 20 * 1024 * 1024  # 20 MB
    MAX_UPLOAD_FILE_COUNT: int = 500
    VERIFICATION_WORKSPACE_DIR: str = "./data/verification_workspaces"

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()

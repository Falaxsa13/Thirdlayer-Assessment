from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./workflow_events.db"

    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 3000
    api_prefix: str = "/api"

    # CORS Configuration
    cors_origins: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # Logging
    log_level: str = "INFO"

    # Application
    app_name: str = "Workflow Event Processor"
    app_version: str = "1.0.0"

    # LLM Configuration
    openai_api_key: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

import os
from typing import Literal
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Base configuration
    PROJECT_NAME: str = f"Geounity API - {os.getenv('ENV', 'development')}"
    DESCRIPTION: str = "API for Geounity project, using FastAPI and SQLModel"
    VERSION: str = "0.0.1"
    ENV: Literal["development", "staging", "production"] = os.getenv("ENV", "development")
    
    # Database configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://seba:123456@localhost:5432/geounity_db")
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "50"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "30"))
    DB_POOL_TIMEOUT: int = int(os.getenv("DB_POOL_TIMEOUT", "60"))
    DB_POOL_RECYCLE: int = int(os.getenv("DB_POOL_RECYCLE", "1800"))
    
    # CORS configuration
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "https://geounity.org"
    ] if ENV == "development" else ["https://geounity.org"]
    
    # Cloudinary configuration
    CLOUDINARY_CLOUD_NAME: str = os.getenv("CLOUDINARY_CLOUD_NAME", "")
    CLOUDINARY_API_KEY: str = os.getenv("CLOUDINARY_API_KEY", "")
    CLOUDINARY_API_SECRET: str = os.getenv("CLOUDINARY_API_SECRET", "")
    
    # Server configuration
    PORT: int = int(os.getenv("PORT", "8080"))

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

settings = Settings()
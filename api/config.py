import os
from typing import Literal
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = f"Geounity API - {os.getenv('ENV', 'development')}"
    DESCRIPTION: str = "API for Geounity project, using FastAPI and SQLModel"
    PORT: int = 8080
    ENV: Literal["development", "staging", "production"] = "development"
    VERSION: str = "0.0.1"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://seba:123456@localhost:5432/geounity_db")
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173/",
        "https://geounity.org/"
    ]
    CLOUDINARY_CLOUD_NAME: str = "geounity"
    CLOUDINARY_API_KEY: str = "813557857562179"
    CLOUDINARY_API_SECRET: str = "cWtbOjvAtiyTk7CJh5Zw6lKZCkQ"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

settings = Settings()
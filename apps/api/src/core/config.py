import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# Search for .env in standard locations
env_locations = [
    Path(r"C:\Users\HomePC\Downloads\Antigravity Applications\Antigravity Creative APP\.env"),
    Path(__file__).resolve().parent.parent.parent.parent / ".env",
    Path(".env")
]

for loc in env_locations:
    if loc.exists():
        load_dotenv(loc)
        break

class Settings:
    PROJECT_NAME: str = "NeedVane Creator AI"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    
    # JWT & Auth
    JWT_SECRET: str = os.getenv("JWT_SECRET", "needvane-super-secret-key-change-in-production-2026")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://needvane.vercel.app"
    ]

settings = Settings()

import os
from dotenv import load_dotenv
from typing import List

# Load environment variables
load_dotenv()

class Settings:
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Chat Service"
    
    # CORS Settings - ensure these include all necessary origins
    BACKEND_CORS_ORIGINS: List[str] = [
        "*",  # Allow all origins
        "http://localhost:3000",
        "http://localhost:3001", 
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:8000",
        "https://goodlife.app"  # Add production domain
    ]
    
    # Service Settings
    MAX_QUERY_LENGTH: int = 500
    DEFAULT_RESPONSE_TIMEOUT: int = 30  # seconds
    
    # OpenAI Settings
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # MongoDB Settings
    MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME", "goodlife")
    
    # JWT Settings
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "secret_key")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

settings = Settings() 
import os
from datetime import timedelta


class Config:
    """Application configuration with sensible defaults."""

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    JWT_ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRES = timedelta(hours=1)

    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_USER = os.getenv("DB_USER", "sms_user")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "sms_pass")
    DB_NAME = os.getenv("DB_NAME", "sms_hub")

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

    RATE_LIMIT = os.getenv("RATE_LIMIT", "10 per minute")
    DEFAULT_SYSTEM_USER = os.getenv("SYSTEM_USERNAME", "family-admin")
    DEFAULT_SYSTEM_PASSWORD = os.getenv("SYSTEM_PASSWORD", "change-me")


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "test-secret-key"
    RATE_LIMIT = "100 per minute"

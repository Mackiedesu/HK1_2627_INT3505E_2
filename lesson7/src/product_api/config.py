"""12-factor configuration hierarchy driven by environment variables."""

import os


class DefaultConfig:
    """Base configuration with sensible defaults for local development."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-not-for-prod")
    JSON_SORT_KEYS = False
    SQLALCHEMY_DATABASE_URI = os.environ.get("DB_URL", "sqlite:///dev.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 1800,
    }
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")


class TestConfig(DefaultConfig):
    """Configuration for automated pytest runs using an in-memory SQLite database."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {}
    LOG_LEVEL = "WARNING"


class ProductionConfig(DefaultConfig):
    """Production configuration with connection pooling and warning log threshold."""

    LOG_LEVEL = "WARNING"
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 10,
        "max_overflow": 20,
        "pool_timeout": 30,
        "pool_recycle": 1800,
        "pool_pre_ping": True,
    }

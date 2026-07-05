"""
config.py
----------
Centralized configuration for the AI Chatbot application.

All configuration values are read from environment variables where
possible, with sensible defaults for local development. Keeping
configuration in one place makes the app easier to deploy across
different environments (local, Render, Railway, PythonAnywhere, etc.)
"""

import os
from pathlib import Path

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent


class Config:
    """Base configuration class."""

    # Flask
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    DEBUG = os.environ.get("FLASK_DEBUG", "True").lower() == "true"
    HOST = os.environ.get("FLASK_HOST", "0.0.0.0")
    PORT = int(os.environ.get("PORT", 5000))

    # Database
    DATABASE_PATH = os.environ.get(
        "DATABASE_PATH", str(BASE_DIR / "database.db")
    )

    # Dialogflow
    DIALOGFLOW_PROJECT_ID = os.environ.get("DIALOGFLOW_PROJECT_ID", "")
    DIALOGFLOW_LANGUAGE_CODE = os.environ.get("DIALOGFLOW_LANGUAGE_CODE", "en")
    DIALOGFLOW_CREDENTIALS_PATH = os.environ.get(
        "DIALOGFLOW_CREDENTIALS_PATH",
        str(BASE_DIR / "dialogflow" / "credentials.json"),
    )
    DIALOGFLOW_SESSION_TIMEOUT = int(
        os.environ.get("DIALOGFLOW_SESSION_TIMEOUT", 3600)
    )

    # CORS
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")

    # Logging
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    LOG_FILE = os.environ.get("LOG_FILE", str(BASE_DIR / "chatbot.log"))


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


class TestingConfig(Config):
    TESTING = True
    DATABASE_PATH = ":memory:"


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}


def get_config():
    """Return the configuration class based on FLASK_ENV."""
    env = os.environ.get("FLASK_ENV", "development")
    return config_by_name.get(env, DevelopmentConfig)

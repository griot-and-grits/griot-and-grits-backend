from pydantic_settings import BaseSettings
from functools import lru_cache
from app.services.db import Database


class AppSettings(BaseSettings):
    mode: str = "dev"
    db_uri: str
    db_name: str = "gngdb"


@lru_cache
def get_settings():
    return AppSettings()


class Factory:
    def __init__(self):
        self.settings = get_settings()
        self.db = Database(
            uri=self.settings.db_uri,
            db_name=self.settings.db_name,
        )


@lru_cache
def get_factory():
    """Singleton factory for the application."""
    return Factory()


# Create the singleton factory instance
factory = get_factory()

__all__ = ["factory", "get_factory", "get_settings"]

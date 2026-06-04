from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


# settings ------------------------------------------------------------------------

# class settings
# - group app     : APP_NAME, APP_VERSION, DEBUG
# - group db      : MONGODB_URI, MONGODB_DATABASE
# - group jwt     : SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
# - group cors    : ALLOWED_ORIGINS
class Settings(BaseSettings):
    # - app
    APP_NAME: str = "SOP-ify API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # - database
    MONGODB_URI: str
    MONGODB_DATABASE: str = "sopifydb"

    # - jwt / security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200  # 30 hari

    # - cors
    ALLOWED_ORIGINS: list[str] = ["*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


# get_settings - balikin instance Settings yang sudah di-cache
# - output : Settings 
# - pake from app.core.config import settings
@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()

# end of settings -----------------------------------------------------------------

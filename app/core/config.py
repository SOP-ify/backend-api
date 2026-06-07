from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


# settings ------------------------------------------------------------------------

# class settings
# - group app     : APP_NAME, APP_VERSION, DEBUG
# - group db      : MONGODB_URI, MONGODB_DATABASE
# - group jwt     : SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
# - group cors    : ALLOWED_ORIGINS
# - group ml      : ML_MODEL_ID, ML_ADAPTER_ID, HUGGINGFACE_TOKEN, WHISPER_MODEL_SIZE
# - group gcs     : GCS_BUCKET_NAME, GCS_CREDENTIALS_JSON
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

    # - machine learning
    ML_MODEL_ID: str = "google/gemma-2-2b-it"
    ML_ADAPTER_ID: str = "iqbalreza/sopify-gemma2-2b-umkm-lora"
    HUGGINGFACE_TOKEN: str | None = None
    WHISPER_MODEL_SIZE: str = "medium"
    # - auto-load model saat startup (True = load di lifespan, False = manual via /ml/load)
    # - set False kalau mau hemat VRAM saat development
    ML_AUTO_LOAD: bool = True
    # - device target untuk inference, "cuda:0" untuk Cloud Run L4 GPU
    CUDA_DEVICE: str = "cuda:0"

    # - google cloud storage
    GCS_BUCKET_NAME: str = "sopify-bucket"
    GCS_CREDENTIALS_JSON: str | None = None  # service account JSON sebagai string

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

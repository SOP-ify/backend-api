# app/core/storage.py
#
# -> Google Cloud Storage client wrapper
#      -> upload file ke sopify-bucket
#      -> balikin public URL
# -> credentials dari GCS_CREDENTIALS_JSON (string JSON service account di .env)
# -> lazy init (client dibuat saat pertama dipakai, bukan saat startup)

import json
import logging
import uuid
from typing import Optional

logger = logging.getLogger(__name__)

_storage_client = None


# init ────────────────────────────────────────────────────────────────────────

# inisialisasi GCS client dari credentials JSON string
# - output : google.cloud.storage.Client
# - error  : RuntimeError kalau GCS_CREDENTIALS_JSON tidak di-set
def _get_client():
    global _storage_client
    if _storage_client is not None:
        return _storage_client

    from app.core.config import settings
    from google.cloud import storage
    from google.oauth2 import service_account

    if not settings.GCS_CREDENTIALS_JSON:
        raise RuntimeError("GCS_CREDENTIALS_JSON tidak di-set di environment")

    creds_dict = json.loads(settings.GCS_CREDENTIALS_JSON)
    credentials = service_account.Credentials.from_service_account_info(
        creds_dict,
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    _storage_client = storage.Client(
        project=creds_dict.get("project_id"),
        credentials=credentials,
    )
    logger.info("GCS: client initialized (bucket=%s)", settings.GCS_BUCKET_NAME)
    return _storage_client

# end of init ─────────────────────────────────────────────────────────────────


# storage operations ──────────────────────────────────────────────────────────

# upload bytes ke GCS dan balikin public URL
# - input  : data (bytes), object_name (str path di bucket, contoh: "diagrams/user_id/uuid.png"),
#            content_type (str, default "image/png")
# - output : str public URL (https://storage.googleapis.com/bucket/object)
# - error  : Exception dari GCS kalau upload gagal
def upload_bytes(
    data: bytes,
    object_name: str,
    content_type: str = "image/png",
) -> str:
    from app.core.config import settings

    client = _get_client()
    bucket = client.bucket(settings.GCS_BUCKET_NAME)
    blob = bucket.blob(object_name)
    blob.upload_from_string(data, content_type=content_type)

    url = f"https://storage.googleapis.com/{settings.GCS_BUCKET_NAME}/{object_name}"
    logger.info("GCS: uploaded %s (%d bytes)", object_name, len(data))
    return url


# hapus object dari GCS
# - input  : object_name (str)
# - output : bool True kalau berhasil, False kalau tidak ditemukan
def delete_object(object_name: str) -> bool:
    from app.core.config import settings

    try:
        client = _get_client()
        bucket = client.bucket(settings.GCS_BUCKET_NAME)
        blob = bucket.blob(object_name)
        blob.delete()
        logger.info("GCS: deleted %s", object_name)
        return True
    except Exception as e:
        logger.warning("GCS: gagal delete %s - %s", object_name, e)
        return False


# generate object name unik untuk diagram
# - input  : user_id (str), ext (str, default ".png")
# - output : str "diagrams/{user_id}/{uuid}.png"
def make_diagram_object_name(user_id: str, ext: str = ".png") -> str:
    return f"diagrams/{user_id}/{uuid.uuid4().hex}{ext}"

# end of storage operations ───────────────────────────────────────────────────

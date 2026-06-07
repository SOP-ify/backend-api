# app/core/database.py
#
# -> async MongoDB client via Motor
#      -> connect saat startup lewat lifespan
#      -> close saat shutdown
# -> get_db() dipakai sebagai FastAPI dependency di setiap router
# -> collection names dikonstanta supaya tidak typo

import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import settings

logger = logging.getLogger(__name__)

# singleton client
_client: AsyncIOMotorClient | None = None


# collections ─────────────────────────────────────────────────────────────────

# nama collection supaya tidak hardcode string di mana-mana
COL_USERS           = "users"
COL_TOKEN_BLACKLIST = "token_blacklist"
COL_SOP_HISTORY     = "sop_history"

# end of collections ──────────────────────────────────────────────────────────


# lifecycle ───────────────────────────────────────────────────────────────────

# buka koneksi ke MongoDB Atlas
# - dipanggil saat lifespan startup di main.py
# - output : None
async def connect_db() -> None:
    global _client
    _client = AsyncIOMotorClient(settings.MONGODB_URI)
    # ping untuk validasi koneksi
    await _client.admin.command("ping")
    logger.info("MongoDB: connected ke %s", settings.MONGODB_DATABASE)


# tutup koneksi MongoDB
# - dipanggil saat lifespan shutdown di main.py
# - output : None
async def close_db() -> None:
    global _client
    if _client:
        _client.close()
        _client = None
    logger.info("MongoDB: connection closed")

# end of lifecycle ────────────────────────────────────────────────────────────


# dependency ──────────────────────────────────────────────────────────────────

# ambil database instance
# - output : AsyncIOMotorDatabase
# - pemakaian : db: AsyncIOMotorDatabase = Depends(get_db)
def get_db() -> AsyncIOMotorDatabase:
    if _client is None:
        raise RuntimeError("MongoDB client belum di-inisialisasi. Pastikan connect_db() sudah dipanggil.")
    return _client[settings.MONGODB_DATABASE]

# end of dependency ───────────────────────────────────────────────────────────

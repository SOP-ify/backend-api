# app/core/database.py
# -> MongoDB connection manager pakai PyMongo

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import settings

_client: AsyncIOMotorClient | None = None
_database: AsyncIOMotorDatabase | None = None


# connection lifecycle ------------------------------------------------------------

# buka koneksi ke MongoDB
async def connect_to_mongo() -> None:
    global _client, _database
    _client = AsyncIOMotorClient(settings.MONGODB_URI)
    _database = _client[settings.MONGODB_DATABASE]

    await _client.admin.command("ping")

async def close_mongo_connection() -> None:
    global _client
    if _client:
        _client.close()
        _client = None

# end of connection lifecycle -----------------------------------------------------


# database accessor ---------------------------------------------------------------
def get_database() -> AsyncIOMotorDatabase:
    if _database is None:
        raise RuntimeError(
            "Database belum diinisialisasi."
        )
    return _database

# ambil collection users
def get_users_collection():
    return get_database()["users"]


# ambil collection token_blacklist
# - note   : dipakai untuk menyimpan token yang sudah di-logout
def get_token_blacklist_collection():
    return get_database()["token_blacklist"]

# end of database accessor --------------------------------------------------------

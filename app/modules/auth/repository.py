# app/modules/auth/repository.py
#
# -> semua query MongoDB untuk auth
#      -> find_user_by_email    : cek login / duplikat register
#      -> find_user_by_id       : fetch user dari JWT sub
#      -> create_user           : insert user baru saat register
#      -> blacklist_token       : logout - simpan JTI ke blacklist
#      -> is_token_blacklisted  : cek apakah token sudah di-logout

import logging
from datetime import datetime, timezone
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db, COL_USERS, COL_TOKEN_BLACKLIST

logger = logging.getLogger(__name__)


# helper ──────────────────────────────────────────────────────────────────────

# konversi dokumen MongoDB (_id: ObjectId) ke dict dengan id: str
# - input  : doc (dict | None)
# - output : dict dengan field "id" (str) menggantikan "_id", atau None
def _serialize(doc: dict | None) -> dict | None:
    if doc is None:
        return None
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    return doc

# end of helper ───────────────────────────────────────────────────────────────


# user queries ────────────────────────────────────────────────────────────────

# cari user berdasarkan email
# - input  : email (str)
# - output : dict user doc dengan "id" (str), atau None kalau tidak ditemukan
async def find_user_by_email(email: str) -> dict | None:
    db: AsyncIOMotorDatabase = get_db()
    doc = await db[COL_USERS].find_one({"email": email})
    return _serialize(doc)


# cari user berdasarkan ObjectId string
# - input  : user_id (str ObjectId)
# - output : dict user doc dengan "id" (str), atau None
async def find_user_by_id(user_id: str) -> dict | None:
    try:
        oid = ObjectId(user_id)
    except Exception:
        return None
    db: AsyncIOMotorDatabase = get_db()
    doc = await db[COL_USERS].find_one({"_id": oid})
    return _serialize(doc)


# insert user baru ke collection users
# - input  : full_name, email, hashed_password, phone_number (keyword args)
# - output : dict user doc dengan "id" dari inserted_id
async def create_user(
    full_name: str,
    email: str,
    hashed_password: str,
    phone_number: str | None = None,
) -> dict:
    now = datetime.now(timezone.utc)
    user_doc = {
        "full_name": full_name,
        "email": email,
        "hashed_password": hashed_password,
        "phone_number": phone_number,
        "username": None,
        "jabatan": None,
        "is_active": True,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    db: AsyncIOMotorDatabase = get_db()
    result = await db[COL_USERS].insert_one(user_doc)
    user_doc["id"] = str(result.inserted_id)
    return user_doc


# update password user (untuk forgot-password flow)
# - input  : user_id (str), hashed_password (str)
# - output : bool True kalau berhasil diupdate
async def update_user_password(user_id: str, hashed_password: str) -> bool:
    try:
        oid = ObjectId(user_id)
    except Exception:
        return False
    db: AsyncIOMotorDatabase = get_db()
    result = await db[COL_USERS].update_one(
        {"_id": oid},
        {"$set": {"hashed_password": hashed_password, "updated_at": datetime.now(timezone.utc)}},
    )
    return result.modified_count > 0

# end of user queries ─────────────────────────────────────────────────────────


# blacklist queries ────────────────────────────────────────────────────────────

# simpan JTI token ke blacklist (saat logout)
# - input  : jti (str UUID dari JWT claim), expires_at (datetime UTC)
# - output : None
# - note   : collection punya TTL index di field expires_at → auto-purge
async def blacklist_token(jti: str, expires_at: datetime) -> None:
    db: AsyncIOMotorDatabase = get_db()
    await db[COL_TOKEN_BLACKLIST].insert_one({
        "jti": jti,
        "expires_at": expires_at,
        "created_at": datetime.now(timezone.utc),
    })
    logger.debug("Auth repo: token %s di-blacklist sampai %s", jti, expires_at)


# cek apakah JTI ada di blacklist
# - input  : jti (str)
# - output : bool True kalau ada di blacklist (sudah logout)
async def is_token_blacklisted(jti: str) -> bool:
    db: AsyncIOMotorDatabase = get_db()
    doc = await db[COL_TOKEN_BLACKLIST].find_one({"jti": jti})
    return doc is not None

# end of blacklist queries ─────────────────────────────────────────────────────

# app/modules/user/repository.py
#
# -> query MongoDB untuk user module
#      -> find_user_by_id      : ambil profil user
#      -> update_user_profile  : partial update profil
#      -> is_username_taken    : cek duplikat username
#      -> count_user_sop       : total SOP user (untuk summary)

import logging
from datetime import datetime, timezone
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional

from app.core.database import get_db, COL_USERS, COL_SOP_HISTORY

logger = logging.getLogger(__name__)


# helper ──────────────────────────────────────────────────────────────────────

# serialize MongoDB doc ke dict dengan id (str)
def _serialize(doc: dict | None) -> dict | None:
    if doc is None:
        return None
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    return doc

# end of helper ───────────────────────────────────────────────────────────────


# user queries ────────────────────────────────────────────────────────────────

# ambil user berdasarkan ObjectId string
# - input  : user_id (str)
# - output : dict user doc atau None
async def find_user_by_id(user_id: str) -> dict | None:
    try:
        oid = ObjectId(user_id)
    except Exception:
        return None
    db: AsyncIOMotorDatabase = get_db()
    doc = await db[COL_USERS].find_one({"_id": oid})
    return _serialize(doc)


# partial update profil user
# - input  : user_id (str), updates (dict field yang berubah saja)
# - output : dict user doc setelah diupdate, atau None kalau user tidak ditemukan
async def update_user_profile(user_id: str, updates: dict) -> dict | None:
    try:
        oid = ObjectId(user_id)
    except Exception:
        return None

    updates["updated_at"] = datetime.now(timezone.utc)
    db: AsyncIOMotorDatabase = get_db()
    result = await db[COL_USERS].find_one_and_update(
        {"_id": oid},
        {"$set": updates},
        return_document=True,
    )
    return _serialize(result)


# cek apakah username sudah dipakai user lain
# - input  : username (str), exclude_user_id (str) — user yang sedang update (boleh punya username sendiri)
# - output : bool True kalau sudah dipakai orang lain
async def is_username_taken(username: str, exclude_user_id: Optional[str] = None) -> bool:
    db: AsyncIOMotorDatabase = get_db()
    query: dict = {"username": username}
    if exclude_user_id:
        try:
            query["_id"] = {"$ne": ObjectId(exclude_user_id)}
        except Exception:
            pass
    doc = await db[COL_USERS].find_one(query, {"_id": 1})
    return doc is not None

# end of user queries ─────────────────────────────────────────────────────────


# stats queries ───────────────────────────────────────────────────────────────

# hitung total SOP yang pernah dibuat user
# - input  : user_id (str)
# - output : int total dokumen sop_history milik user
async def count_user_sop(user_id: str) -> int:
    db: AsyncIOMotorDatabase = get_db()
    return await db[COL_SOP_HISTORY].count_documents({"user_id": user_id})

# end of stats queries ────────────────────────────────────────────────────────

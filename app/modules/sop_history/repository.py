# app/modules/sop_history/repository.py
#
# -> query MongoDB untuk riwayat SOP
#      -> insert_sop          : simpan SOP baru
#      -> list_sop_by_user    : list riwayat paginated
#      -> find_sop_by_id      : detail satu SOP
#      -> delete_sop          : hapus SOP (hanya milik user sendiri)
#      -> count_sop_by_user   : total SOP untuk pagination

import logging
from datetime import datetime, timezone
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional

from app.core.database import get_db, COL_SOP_HISTORY

logger = logging.getLogger(__name__)


# helper ──────────────────────────────────────────────────────────────────────

# serialize MongoDB doc ke dict dengan id (str) dan created_at (str ISO)
def _serialize(doc: dict | None) -> dict | None:
    if doc is None:
        return None
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    # pastikan created_at jadi string ISO
    if isinstance(doc.get("created_at"), datetime):
        doc["created_at"] = doc["created_at"].isoformat()
    return doc

# end of helper ───────────────────────────────────────────────────────────────


# sop_history queries ─────────────────────────────────────────────────────────

# insert SOP baru ke collection sop_history
# - input  : sop_doc (dict, sudah include user_id, semua field lengkap)
# - output : dict sop doc dengan "id" dari inserted_id
async def insert_sop(sop_doc: dict) -> dict:
    db: AsyncIOMotorDatabase = get_db()
    result = await db[COL_SOP_HISTORY].insert_one(sop_doc)
    sop_doc["id"] = str(result.inserted_id)
    return sop_doc


# list riwayat SOP milik user (paginated, urut terbaru dulu)
# - input  : user_id (str), page (int ≥1), limit (int 1-50)
# - output : list[dict] — hanya field ringkasan (tidak include sop full + catatan)
async def list_sop_by_user(user_id: str, page: int = 1, limit: int = 10) -> list[dict]:
    db: AsyncIOMotorDatabase = get_db()
    skip = (page - 1) * limit
    projection = {
        "catatan": 0,   # tidak tampil di list (terlalu panjang)
        "sop": 0,       # tidak tampil di list
        "steps": 0,     # tidak tampil di list
    }
    cursor = (
        db[COL_SOP_HISTORY]
        .find({"user_id": user_id}, projection)
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    docs = await cursor.to_list(length=limit)
    return [_serialize(d) for d in docs]


# ambil detail satu SOP berdasarkan id
# - input  : sop_id (str ObjectId)
# - output : dict sop doc lengkap, atau None
async def find_sop_by_id(sop_id: str) -> dict | None:
    try:
        oid = ObjectId(sop_id)
    except Exception:
        return None
    db: AsyncIOMotorDatabase = get_db()
    doc = await db[COL_SOP_HISTORY].find_one({"_id": oid})
    return _serialize(doc)


# hapus SOP — hanya kalau memang milik user tersebut
# - input  : sop_id (str ObjectId), user_id (str) untuk validasi kepemilikan
# - output : bool True kalau berhasil dihapus, False kalau tidak ditemukan / bukan milik user
async def delete_sop(sop_id: str, user_id: str) -> bool:
    try:
        oid = ObjectId(sop_id)
    except Exception:
        return False
    db: AsyncIOMotorDatabase = get_db()
    result = await db[COL_SOP_HISTORY].delete_one({"_id": oid, "user_id": user_id})
    return result.deleted_count > 0


# hitung total SOP milik user (untuk pagination)
# - input  : user_id (str)
# - output : int
async def count_sop_by_user(user_id: str) -> int:
    db: AsyncIOMotorDatabase = get_db()
    return await db[COL_SOP_HISTORY].count_documents({"user_id": user_id})

# end of sop_history queries ──────────────────────────────────────────────────


# aliases ─────────────────────────────────────────────────────────────────────
# nama pendek yang dipakai di tests dan service sebagai alternatif

find_by_user  = list_sop_by_user
count_by_user = count_sop_by_user
find_by_id    = find_sop_by_id
delete_by_id  = delete_sop

# end of aliases ──────────────────────────────────────────────────────────────

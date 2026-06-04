# app/modules/auth/repository.py
#
# -> data access layer untuk modul auth
#      -> semua query MongoDB ada di sini

from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId
from typing import Optional
from app.core.database import get_users_collection, get_token_blacklist_collection


# type alias biar lebih jelas waktu baca signature function
UserDocument = dict


# helper --------------------------------------------------------------------------

# konversi raw MongoDB
# - input  : doc (dict hasil find_one MongoDB, ada field _id sebagai ObjectId)
# - output : doc yang sama tapi _id -> id (str), datetime -> ISO string
def _serialize_user(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    if isinstance(doc.get("created_at"), datetime):
        doc["created_at"] = doc["created_at"].isoformat()
    if isinstance(doc.get("updated_at"), datetime):
        doc["updated_at"] = doc["updated_at"].isoformat()
    return doc

# end of helper ------------------------------------------------------------------


# user queries --------------------------------------------------------------------

# cari user berdasarkan email (case-insensitive, all lowercase)
# - input  : email (str)
# - output : UserDocument (dict) kalau ketemu, None kalau tidak ada
async def find_user_by_email(email: str) -> Optional[UserDocument]:
    collection = get_users_collection()
    doc = await collection.find_one({"email": email.lower()})
    if doc:
        return _serialize_user(doc)
    return None


# cari user berdasarkan MongoDB ObjectId
# - input  : user_id (str ObjectId)
# - output : UserDocument (dict) kalau ketemu, None kalau tidak ada atau id invalid
async def find_user_by_id(user_id: str) -> Optional[UserDocument]:
    try:
        obj_id = ObjectId(user_id)
    except InvalidId:
        return None

    collection = get_users_collection()
    doc = await collection.find_one({"_id": obj_id})
    if doc:
        return _serialize_user(doc)
    return None


# insert user baru ke collection users
# - input  : full_name, email, hashed_password, phone_number (opsional)
# - output : UserDocument (dict) dari dokumen yang baru diinsert
async def create_user(
    full_name: str,
    email: str,
    hashed_password: str,
    phone_number: Optional[str] = None,
) -> UserDocument:
    now = datetime.now(timezone.utc)
    user_doc = {
        "full_name": full_name,
        "email": email.lower(),
        "hashed_password": hashed_password,
        "phone_number": phone_number,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    collection = get_users_collection()
    result = await collection.insert_one(user_doc)
    user_doc["_id"] = result.inserted_id
    return _serialize_user(user_doc)


# update field hashed_password user
# - input  : user_id (str ObjectId), hashed_password (str Argon2 hash)
# - output : True kalau berhasil diupdate, False kalau user tidak ditemukan
async def update_user_password(user_id: str, hashed_password: str) -> bool:
    try:
        obj_id = ObjectId(user_id)
    except InvalidId:
        return False

    collection = get_users_collection()
    result = await collection.update_one(
        {"_id": obj_id},
        {
            "$set": {
                "hashed_password": hashed_password,
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )
    return result.modified_count > 0

# end of user queries -------------------------------------------------------------


# token blacklist -----------------------------------------------------------------

# masukin JTI token ke blacklist - dipake waktu logout
# - input  : jti (str UUID dari payload JWT), expires_at (datetime UTC kapan token expired)
# - output : None
# - note   : MongoDB TTL index di field expires_at akan auto-hapus dokumen yang sudah expired
async def blacklist_token(jti: str, expires_at: datetime) -> None:
    collection = get_token_blacklist_collection()
    await collection.insert_one({"jti": jti, "expires_at": expires_at})


# cek apakah JTI token ada di blacklist (sudah di-logout)
# - input  : jti (str UUID)
# - output : True kalau token sudah diblacklist, False kalau masih valid
async def is_token_blacklisted(jti: str) -> bool:
    collection = get_token_blacklist_collection()
    doc = await collection.find_one({"jti": jti})
    return doc is not None

# end of token blacklist ----------------------------------------------------------


# index setup ---------------------------------------------------------------------

# buat indexes MongoDB yang dibutuhin
# - output : None
# - indexes yang dibuat:
#     -> users.email     : unique index untuk cari by email dan prevent duplicate
#     -> blacklist.expires_at : TTL index, MongoDB auto-hapus token yang expired
async def ensure_indexes() -> None:
    users = get_users_collection()
    blacklist = get_token_blacklist_collection()

    await users.create_index("email", unique=True)
    await blacklist.create_index("expires_at", expireAfterSeconds=0)

# end of index setup --------------------------------------------------------------

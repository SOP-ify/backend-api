# app/modules/user/service.py
#
# -> business logic user module
#      -> get_profile    : ambil profil user lengkap
#      -> update_profile : partial update, validasi username duplikat
#      -> get_summary    : statistik total SOP user

from app.modules.user import repository
from app.modules.user.schemas import UpdateProfileRequest, UserProfileResponse, UserSummaryResponse
from app.shared.exceptions import not_found_exception, bad_request_exception


# helper ──────────────────────────────────────────────────────────────────────

# bangun UserProfileResponse dari user doc MongoDB
# - input  : doc (dict user dari DB)
# - output : UserProfileResponse
def _build_profile(doc: dict) -> UserProfileResponse:
    return UserProfileResponse(
        id=doc["id"],
        full_name=doc.get("full_name", ""),
        email=doc.get("email", ""),
        phone_number=doc.get("phone_number"),
        username=doc.get("username"),
        jabatan=doc.get("jabatan"),
        is_active=doc.get("is_active", True),
        created_at=str(doc.get("created_at", "")),
    )

# end of helper ───────────────────────────────────────────────────────────────


# user operations ─────────────────────────────────────────────────────────────

# ambil profil lengkap user yang login
# - input  : user_id (str ObjectId)
# - output : UserProfileResponse
# - error  : 404 kalau user tidak ditemukan
async def get_profile(user_id: str) -> UserProfileResponse:
    doc = await repository.find_user_by_id(user_id)
    if not doc:
        raise not_found_exception("User")
    return _build_profile(doc)


# partial update profil user
# - input  : user_id (str), payload UpdateProfileRequest
# - output : UserProfileResponse setelah diupdate
# - error  : 404 kalau user tidak ditemukan
#            409 kalau username sudah dipakai user lain
async def update_profile(user_id: str, payload: UpdateProfileRequest) -> UserProfileResponse:
    # hanya ambil field yang di-set (tidak None)
    updates = payload.model_dump(exclude_none=True)
    if not updates:
        # tidak ada yang diubah, return profil yang ada
        doc = await repository.find_user_by_id(user_id)
        if not doc:
            raise not_found_exception("User")
        return _build_profile(doc)

    # cek duplikat username kalau username ada di updates
    if "username" in updates:
        taken = await repository.is_username_taken(
            username=updates["username"],
            exclude_user_id=user_id,
        )
        if taken:
            raise bad_request_exception("Username sudah digunakan, coba yang lain")

    updated_doc = await repository.update_user_profile(user_id=user_id, updates=updates)
    if not updated_doc:
        raise not_found_exception("User")
    return _build_profile(updated_doc)


# ambil ringkasan statistik user
# - input  : user_id (str)
# - output : UserSummaryResponse { user_id, total_sop }
# - error  : 404 kalau user tidak ditemukan
async def get_summary(user_id: str) -> UserSummaryResponse:
    from app.modules.sop_history.repository import count_by_user

    doc = await repository.find_user_by_id(user_id)
    if not doc:
        raise not_found_exception("User")

    total = await count_by_user(user_id=user_id)
    return UserSummaryResponse(user_id=user_id, total_sop=total)

# end of user operations ──────────────────────────────────────────────────────

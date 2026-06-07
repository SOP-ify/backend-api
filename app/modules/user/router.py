# app/modules/user/router.py
#
# -> HTTP endpoints user module
#      -> GET  /user/me          : profil lengkap user
#      -> PUT  /user/me          : partial update profil
#      -> GET  /user/me/summary  : statistik total SOP user

from fastapi import APIRouter, Depends, status

from app.modules.auth.dependencies import get_current_user
from app.modules.user import service
from app.modules.user.schemas import UpdateProfileRequest
from app.shared.response import success_response

router = APIRouter(prefix="/api/v1/user", tags=["User"])


# endpoints ───────────────────────────────────────────────────────────────────

# GET /user/me — profil lengkap user yang login
# - input  : Authorization Bearer token
# - output : { success, message, data: UserProfileResponse }
# - error  : 401 kalau tidak ada token valid
@router.get(
    "/me",
    status_code=status.HTTP_200_OK,
    summary="Profil User",
    description="Ambil profil lengkap user yang sedang login.",
)
async def get_profile(current_user: dict = Depends(get_current_user)) -> dict:
    profile = await service.get_profile(user_id=current_user["id"])
    return success_response(
        message="Profil berhasil diambil",
        data=profile.model_dump(),
    )


# PUT /user/me — partial update profil (full_name, username, jabatan)
# - input  : Authorization Bearer token + UpdateProfileRequest body (semua field optional)
# - output : { success, message, data: UserProfileResponse }
# - error  : 401, 404 user tidak ditemukan, 409 username duplikat, 422 validasi
@router.put(
    "/me",
    status_code=status.HTTP_200_OK,
    summary="Update Profil",
    description="Update profil user. Semua field bersifat opsional (partial update).",
)
async def update_profile(
    payload: UpdateProfileRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    updated = await service.update_profile(user_id=current_user["id"], payload=payload)
    return success_response(
        message="Profil berhasil diperbarui",
        data=updated.model_dump(),
    )


# GET /user/me/summary — statistik singkat user
# - input  : Authorization Bearer token
# - output : { success, message, data: { user_id, total_sop } }
# - error  : 401, 404
@router.get(
    "/me/summary",
    status_code=status.HTTP_200_OK,
    summary="Ringkasan User",
    description="Statistik singkat user: total SOP yang pernah dibuat.",
)
async def get_summary(current_user: dict = Depends(get_current_user)) -> dict:
    summary = await service.get_summary(user_id=current_user["id"])
    return success_response(
        message="Ringkasan berhasil diambil",
        data=summary.model_dump(),
    )

# end of endpoints ────────────────────────────────────────────────────────────

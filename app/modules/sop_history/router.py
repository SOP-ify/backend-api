# app/modules/sop_history/router.py
#
# -> HTTP endpoints untuk riwayat SOP
#      -> POST   /sop          : simpan SOP ke riwayat
#      -> GET    /sop          : list riwayat (paginated)
#      -> GET    /sop/{id}     : detail satu SOP
#      -> DELETE /sop/{id}     : hapus SOP dari riwayat

from fastapi import APIRouter, Depends, Query, status

from app.modules.auth.dependencies import get_current_user
from app.modules.sop_history import service
from app.modules.sop_history.schemas import SaveSOPRequest
from app.shared.response import success_response

router = APIRouter(prefix="/api/v1/sop", tags=["Riwayat SOP"])


# endpoints ───────────────────────────────────────────────────────────────────

# POST /sop — simpan SOP yang sudah digenerate ke riwayat
# - input  : Authorization + SaveSOPRequest body
# - output : { success, message, data: SOPHistoryDetail }
# - error  : 401, 422
@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Simpan SOP ke Riwayat",
    description="Menyimpan hasil generate SOP beserta input catatan ke riwayat.",
)
async def save_sop(
    payload: SaveSOPRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    result = await service.save_sop(user_id=current_user["id"], payload=payload)
    return success_response(
        message="SOP berhasil disimpan",
        data=result.model_dump(),
    )


# GET /sop — list riwayat SOP user (paginated, terbaru dulu)
# - input  : Authorization + query params page, limit
# - output : { success, message, data: SOPListResponse }
# - error  : 401
@router.get(
    "",
    status_code=status.HTTP_200_OK,
    summary="List Riwayat SOP",
    description="Ambil daftar riwayat SOP yang pernah dibuat user. Diurutkan dari yang terbaru.",
)
async def list_sop(
    page: int = Query(default=1, ge=1, description="Halaman (mulai dari 1)"),
    limit: int = Query(default=10, ge=1, le=50, description="Jumlah item per halaman (max 50)"),
    current_user: dict = Depends(get_current_user),
) -> dict:
    result = await service.list_sop(user_id=current_user["id"], page=page, limit=limit)
    return success_response(
        message="Riwayat SOP berhasil diambil",
        data=result.model_dump(),
    )


# GET /sop/{id} — detail satu SOP (include catatan input + sop output)
# - input  : Authorization + sop_id path param
# - output : { success, message, data: SOPHistoryDetail }
# - error  : 401, 403 (bukan milik user), 404
@router.get(
    "/{sop_id}",
    status_code=status.HTTP_200_OK,
    summary="Detail SOP",
    description="Ambil detail lengkap satu SOP termasuk input catatan dan output SOP yang dihasilkan.",
)
async def get_sop(
    sop_id: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    result = await service.get_sop(sop_id=sop_id, user_id=current_user["id"])
    return success_response(
        message="Detail SOP berhasil diambil",
        data=result.model_dump(),
    )


# DELETE /sop/{id} — hapus SOP dari riwayat
# - input  : Authorization + sop_id path param
# - output : { success, message }
# - error  : 401, 404 (tidak ditemukan atau bukan milik user)
@router.delete(
    "/{sop_id}",
    status_code=status.HTTP_200_OK,
    summary="Hapus SOP",
    description="Menghapus SOP dari riwayat. Hanya bisa menghapus SOP milik sendiri.",
)
async def delete_sop(
    sop_id: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    await service.remove_sop(sop_id=sop_id, user_id=current_user["id"])
    return success_response(message="SOP berhasil dihapus")

# end of endpoints ────────────────────────────────────────────────────────────

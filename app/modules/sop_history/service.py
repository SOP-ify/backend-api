# app/modules/sop_history/service.py
#
# -> business logic riwayat SOP
#      -> save_sop    : validasi + simpan SOP baru ke riwayat
#      -> list_sop    : ambil list paginated riwayat user
#      -> get_sop     : detail satu SOP (validasi kepemilikan)
#      -> remove_sop  : hapus SOP (validasi kepemilikan)

from datetime import datetime, timezone

from app.modules.sop_history import repository
from app.modules.sop_history.schemas import (
    SaveSOPRequest,
    SOPHistoryItem,
    SOPHistoryDetail,
    SOPListResponse,
    StepItem,
)
from app.shared.exceptions import not_found_exception, forbidden_exception


# helper ──────────────────────────────────────────────────────────────────────

# bangun SOPHistoryDetail dari raw MongoDB doc
def _to_detail(doc: dict) -> SOPHistoryDetail:
    steps = [StepItem(**s) for s in doc.get("steps", [])]
    return SOPHistoryDetail(
        id=doc["id"],
        user_id=doc["user_id"],
        sop_name=doc["sop_name"],
        kategori=doc.get("kategori", ""),
        catatan=doc.get("catatan", ""),
        sop=doc.get("sop", ""),
        style=doc.get("style", "dokumen_terstruktur"),
        steps=steps,
        step_count=doc.get("step_count", len(steps)),
        valid=doc.get("valid", True),
        attempt=doc.get("attempt", 1),
        generation_time_seconds=doc.get("generation_time_seconds"),
        created_at=str(doc.get("created_at", "")),
    )


# bangun SOPHistoryItem (ringkasan) dari raw doc
def _to_item(doc: dict) -> SOPHistoryItem:
    return SOPHistoryItem(
        id=doc["id"],
        user_id=doc["user_id"],
        sop_name=doc["sop_name"],
        kategori=doc.get("kategori", ""),
        style=doc.get("style", "dokumen_terstruktur"),
        step_count=doc.get("step_count", 0),
        created_at=str(doc.get("created_at", "")),
    )

# end of helper ───────────────────────────────────────────────────────────────


# sop operations ──────────────────────────────────────────────────────────────

# simpan SOP baru ke riwayat
# - input  : user_id (str), payload SaveSOPRequest
# - output : SOPHistoryDetail dokumen yang baru disimpan
async def save_sop(user_id: str, payload: SaveSOPRequest) -> SOPHistoryDetail:
    doc = {
        "user_id": user_id,
        "sop_name": payload.sop_name,
        "kategori": payload.kategori,
        "catatan": payload.catatan,
        "sop": payload.sop,
        "style": payload.style,
        "steps": [s.model_dump() for s in payload.steps],
        "step_count": payload.step_count,
        "valid": payload.valid,
        "attempt": payload.attempt,
        "generation_time_seconds": payload.generation_time_seconds,
        "created_at": datetime.now(timezone.utc),
    }
    saved = await repository.insert_sop(doc)
    return _to_detail(saved)


# list riwayat SOP user (paginated, terbaru dulu)
# - input  : user_id (str), page (int ≥1), limit (int 1-50)
# - output : SOPListResponse { items, total, page, limit, has_next }
async def list_sop(user_id: str, page: int = 1, limit: int = 10) -> SOPListResponse:
    limit = max(1, min(50, limit))
    page = max(1, page)

    docs = await repository.find_by_user(user_id=user_id, page=page, limit=limit)
    total = await repository.count_by_user(user_id=user_id)
    items = [_to_item(d) for d in docs]

    return SOPListResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        has_next=(page * limit) < total,
    )


# ambil detail SOP berdasarkan id
# - input  : sop_id (str), user_id (str) untuk verifikasi kepemilikan
# - output : SOPHistoryDetail
# - error  : 404 kalau tidak ditemukan, 403 kalau bukan milik user
async def get_sop(sop_id: str, user_id: str) -> SOPHistoryDetail:
    doc = await repository.find_by_id(sop_id)
    if not doc:
        raise not_found_exception("SOP")
    if doc["user_id"] != user_id:
        raise forbidden_exception("Anda tidak berhak mengakses SOP ini")
    return _to_detail(doc)


# hapus SOP
# - input  : sop_id (str), user_id (str)
# - output : None
# - error  : 404 kalau tidak ditemukan atau bukan milik user
async def remove_sop(sop_id: str, user_id: str) -> None:
    deleted = await repository.delete_by_id(sop_id=sop_id, user_id=user_id)
    if not deleted:
        raise not_found_exception("SOP")

# end of sop operations ───────────────────────────────────────────────────────

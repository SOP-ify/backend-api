# app/modules/sop_history/schemas.py
#
# -> request dan response schema untuk riwayat SOP
#      -> StepItem          : satu langkah SOP
#      -> SaveSOPRequest    : body untuk POST /sop
#      -> SOPHistoryItem    : satu item di list riwayat (ringkasan)
#      -> SOPHistoryDetail  : detail lengkap satu SOP (input + output)
#      -> SOPListResponse   : hasil GET /sop (paginated list)

from pydantic import BaseModel, field_validator
from typing import Optional


# sub-models ──────────────────────────────────────────────────────────────────

# satu langkah dalam SOP yang sudah di-parse
# - fields  : no (int), judul (str), deskripsi (str), pic (str | None), durasi (str | None)
class StepItem(BaseModel):
    no: int
    judul: str
    deskripsi: str
    pic: Optional[str] = None
    durasi: Optional[str] = None

# end of sub-models ───────────────────────────────────────────────────────────


# request schemas ─────────────────────────────────────────────────────────────

# body untuk POST /sop — simpan hasil generate SOP ke riwayat
# - fields  : sop_name, kategori, catatan (input user), sop (output AI),
#             style, steps, step_count, valid, attempt, generation_time_seconds
class SaveSOPRequest(BaseModel):
    sop_name: str
    kategori: str
    catatan: str
    sop: str
    style: str = "dokumen_terstruktur"
    steps: list[StepItem] = []
    step_count: int = 0
    valid: bool = True
    attempt: int = 1
    generation_time_seconds: Optional[float] = None

    @field_validator("sop_name")
    @classmethod
    def sop_name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Nama SOP tidak boleh kosong")
        return v.strip()

    @field_validator("catatan")
    @classmethod
    def catatan_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Catatan tidak boleh kosong")
        return v.strip()

    @field_validator("sop")
    @classmethod
    def sop_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Konten SOP tidak boleh kosong")
        return v.strip()

# end of request schemas ──────────────────────────────────────────────────────


# response schemas ────────────────────────────────────────────────────────────

# satu item di list riwayat (ringkasan, tidak include sop full)
# - fields  : id, user_id, sop_name, kategori, style, step_count, created_at
class SOPHistoryItem(BaseModel):
    id: str
    user_id: str
    sop_name: str
    kategori: str
    style: str
    step_count: int
    created_at: str


# detail lengkap satu SOP — include input catatan + output sop + steps
# - fields  : SOPHistoryItem fields + catatan, sop, steps, valid, generation_time_seconds
class SOPHistoryDetail(BaseModel):
    id: str
    user_id: str
    sop_name: str
    kategori: str
    catatan: str
    sop: str
    style: str
    steps: list[StepItem]
    step_count: int
    valid: bool
    attempt: int
    generation_time_seconds: Optional[float]
    created_at: str


# response untuk GET /sop (paginated list)
# - fields  : items (list SOPHistoryItem), total, page, limit, has_next
class SOPListResponse(BaseModel):
    items: list[SOPHistoryItem]
    total: int
    page: int
    limit: int
    has_next: bool

# end of response schemas ─────────────────────────────────────────────────────

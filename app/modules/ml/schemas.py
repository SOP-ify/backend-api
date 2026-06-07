# app/modules/ml/schemas.py
#
# -> request dan response schema untuk ML module
#      -> TextToSOPRequest    : body untuk POST /ml/text-to-sop
#      -> AudioToTextRequest  : metadata untuk POST /ml/audio-to-text (file via Form)
#      -> DiagramToPNGRequest : body untuk POST /ml/diagram-to-png
#      -> SOPResponse         : response generate SOP
#      -> TranscriptResponse  : response transkrip audio
#      -> DiagramResponse     : response upload diagram PNG
#      -> MLStatusResponse    : status model

from pydantic import BaseModel, field_validator
from typing import Optional


# request schemas ─────────────────────────────────────────────────────────────

# body untuk POST /ml/text-to-sop
# - fields : sop_name, kategori, catatan (input user), style (SOPStyle string)
class TextToSOPRequest(BaseModel):
    sop_name: str
    kategori: str
    catatan: str
    style: str = "dokumen_terstruktur"
    max_new_tokens: int = 512
    temperature: float = 0.7

    @field_validator("catatan")
    @classmethod
    def catatan_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Catatan tidak boleh kosong")
        return v.strip()

    @field_validator("sop_name")
    @classmethod
    def sop_name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Nama SOP tidak boleh kosong")
        return v.strip()

    @field_validator("style")
    @classmethod
    def validate_style(cls, v: str) -> str:
        valid = {"dokumen_terstruktur", "chat_wa", "instruksi_lisan", "diagram_mermaid", "kolom_tabel", "fine_tune"}
        if v not in valid:
            raise ValueError(f"Style tidak valid. Pilihan: {', '.join(sorted(valid))}")
        return v

    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        if not 0.1 <= v <= 1.5:
            raise ValueError("Temperature harus antara 0.1 dan 1.5")
        return v

    @field_validator("max_new_tokens")
    @classmethod
    def validate_max_tokens(cls, v: int) -> int:
        if not 64 <= v <= 1024:
            raise ValueError("max_new_tokens harus antara 64 dan 1024")
        return v


# body untuk POST /ml/diagram-to-png
class DiagramToPNGRequest(BaseModel):
    mermaid_text: str

    @field_validator("mermaid_text")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("mermaid_text tidak boleh kosong")
        return v.strip()

# end of request schemas ──────────────────────────────────────────────────────


# response schemas ────────────────────────────────────────────────────────────

# satu langkah SOP yang sudah di-parse
class StepItemResponse(BaseModel):
    no: int
    judul: str
    deskripsi: str
    pic: Optional[str] = None
    durasi: Optional[str] = None


# response POST /ml/text-to-sop
# - fields : sop, steps, step_count, valid, generation_time_seconds
class SOPResponse(BaseModel):
    sop: str
    steps: list[StepItemResponse]
    step_count: int
    valid: bool
    generation_time_seconds: float


# response POST /ml/audio-to-text
# - fields : transcript, duration_seconds, duration_formatted, word_count
class TranscriptResponse(BaseModel):
    transcript: str
    duration_seconds: float
    duration_formatted: str
    word_count: int


# response POST /ml/diagram-to-png
# - fields : url (public GCS URL), object_name, size_bytes
class DiagramResponse(BaseModel):
    url: str
    object_name: str
    size_bytes: int


# response GET /ml/status
class MLStatusResponse(BaseModel):
    sop_generator_loaded: bool
    sop_generator_device: Optional[str]
    stt_engine_loaded: bool
    stt_engine_device: Optional[str]

# end of response schemas ─────────────────────────────────────────────────────

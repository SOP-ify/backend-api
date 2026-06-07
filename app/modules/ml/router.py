# app/modules/ml/router.py
#
# -> HTTP endpoints untuk ML module
#      -> POST /ml/load          : load model ke GPU/CPU
#      -> POST /ml/unload        : unload model
#      -> GET  /ml/status        : status model (loaded/not, device)
#      -> POST /ml/audio-to-text : upload audio → transkrip (Whisper)
#      -> POST /ml/text-to-sop   : teks catatan → SOP (Gemma + LoRA)
#      -> POST /ml/diagram-to-png : mermaid string → PNG → GCS URL

import logging
from fastapi import APIRouter, Depends, File, Form, UploadFile, status, HTTPException

from app.modules.auth.dependencies import get_current_user
from app.modules.ml import service
from app.modules.ml.schemas import TextToSOPRequest, DiagramToPNGRequest
from app.modules.ml.engine.sop_generator import get_sop_generator
from app.modules.ml.engine.stt_engine import get_stt_engine
from app.shared.response import success_response
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/ml", tags=["Machine Learning"])


# endpoints ───────────────────────────────────────────────────────────────────

# POST /ml/load — load model ke memori (GPU kalau tersedia, CPU kalau tidak)
# - output : { success, message, data: { device, sop_loaded, stt_loaded } }
# - note   : bisa dipanggil ulang tanpa masalah (idempotent)
@router.post(
    "/load",
    status_code=status.HTTP_200_OK,
    summary="Load ML Model",
    description="Muat model Gemma 2 + LoRA dan Whisper ke memory GPU/CPU.",
)
async def load_model(current_user: dict = Depends(get_current_user)) -> dict:
    import torch

    device = settings.CUDA_DEVICE if torch.cuda.is_available() else "cpu"

    # load SOP generator
    generator = get_sop_generator(
        model_id=settings.ML_MODEL_ID,
        adapter_id=settings.ML_ADAPTER_ID,
        hf_token=settings.HUGGINGFACE_TOKEN,
    )
    if not generator.is_loaded():
        generator.load(device=device)

    # load STT engine
    stt = get_stt_engine(model_size=settings.WHISPER_MODEL_SIZE)
    if not stt.is_loaded():
        stt.load()

    return success_response(
        message=f"Model berhasil di-load ke {device}",
        data={
            "device": device,
            "sop_generator_loaded": generator.is_loaded(),
            "stt_loaded": stt.is_loaded(),
        },
    )


# POST /ml/unload — unload model dari memori (bebaskan VRAM)
# - output : { success, message }
@router.post(
    "/unload",
    status_code=status.HTTP_200_OK,
    summary="Unload ML Model",
    description="Hapus model dari memory untuk membebaskan GPU/RAM.",
)
async def unload_model(current_user: dict = Depends(get_current_user)) -> dict:
    generator = get_sop_generator()
    generator.unload()

    stt = get_stt_engine()
    stt.unload()

    return success_response(message="Model berhasil di-unload dari memory")


# GET /ml/status — cek status model
# - output : { success, message, data: MLStatusResponse }
@router.get(
    "/status",
    status_code=status.HTTP_200_OK,
    summary="Status Model",
    description="Cek apakah model sudah di-load dan di device mana.",
)
async def model_status(current_user: dict = Depends(get_current_user)) -> dict:
    generator = get_sop_generator()
    stt = get_stt_engine()

    return success_response(
        message="Status model",
        data={
            "sop_generator_loaded": generator.is_loaded(),
            "sop_generator_device": generator.device,
            "stt_engine_loaded": stt.is_loaded(),
            "stt_engine_device": stt._device,
        },
    )


# POST /ml/audio-to-text — transkrip audio ke teks via Whisper
# - input  : audio file (UploadFile), language (Form field, default "id")
# - output : { success, message, data: TranscriptResponse }
# - error  : 400 kalau STT belum load, 422 kalau file tidak valid
@router.post(
    "/audio-to-text",
    status_code=status.HTTP_200_OK,
    summary="Audio ke Teks",
    description="Upload file audio (mp3/wav/m4a/webm) dan dapatkan transkripnya menggunakan Whisper.",
)
async def audio_to_text(
    audio: UploadFile = File(..., description="File audio (mp3, wav, m4a, webm)"),
    language: str = Form(default="id", description="Kode bahasa (default: id untuk Indonesia)"),
    current_user: dict = Depends(get_current_user),
) -> dict:
    stt = get_stt_engine()
    if not stt.is_loaded():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="STT model belum di-load. Panggil POST /api/v1/ml/load terlebih dahulu.",
        )

    audio_bytes = await audio.read()
    result = await service.transcribe_audio(
        audio_bytes=audio_bytes,
        filename=audio.filename or "audio.mp3",
        language=language,
    )

    return success_response(
        message="Audio berhasil ditranskrip",
        data=result.model_dump(),
    )


# POST /ml/text-to-sop — generate SOP dari teks catatan
# - input  : TextToSOPRequest body
# - output : { success, message, data: SOPResponse }
# - error  : 503 kalau model belum load
@router.post(
    "/text-to-sop",
    status_code=status.HTTP_200_OK,
    summary="Teks ke SOP",
    description="Generate SOP dari catatan proses kerja UMKM menggunakan Gemma 2 + LoRA.",
)
async def text_to_sop(
    payload: TextToSOPRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    generator = get_sop_generator()
    if not generator.is_loaded():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SOP model belum di-load. Panggil POST /api/v1/ml/load terlebih dahulu.",
        )

    result = await service.generate_sop(
        sop_name=payload.sop_name,
        kategori=payload.kategori,
        catatan=payload.catatan,
        style=payload.style,
        max_new_tokens=payload.max_new_tokens,
        temperature=payload.temperature,
    )

    return success_response(
        message="SOP berhasil digenerate",
        data=result.model_dump(),
    )


# POST /ml/diagram-to-png — render mermaid ke PNG dan upload ke GCS
# - input  : DiagramToPNGRequest { mermaid_text }
# - output : { success, message, data: DiagramResponse }
@router.post(
    "/diagram-to-png",
    status_code=status.HTTP_200_OK,
    summary="Diagram ke PNG",
    description="Konversi Mermaid.js diagram menjadi PNG dan simpan ke Google Cloud Storage.",
)
async def diagram_to_png(
    payload: DiagramToPNGRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    result = await service.render_diagram(
        mermaid_text=payload.mermaid_text,
        user_id=current_user["id"],
    )

    return success_response(
        message="Diagram berhasil di-render dan diupload",
        data=result.model_dump(),
    )

# end of endpoints ────────────────────────────────────────────────────────────

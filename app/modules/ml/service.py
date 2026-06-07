# app/modules/ml/service.py
#
# -> orkestrasi semua ML engine
#      -> generate_sop      : text → SOP via SOPGenerator + prompts + postprocessor
#      -> transcribe_audio  : audio bytes → transkrip via STTEngine
#      -> render_diagram    : mermaid string → PNG → GCS URL
# -> service ini tidak tahu soal HTTP, hanya terima/balikin data

import time
import logging
from typing import Optional

from app.modules.ml.engine.sop_generator import get_sop_generator
from app.modules.ml.engine.stt_engine import get_stt_engine
from app.modules.ml.engine.diagram_renderer import render_and_upload
from app.modules.ml.engine.postprocessor import clean_output, parse_steps_from_sop, validate_output
from app.modules.ml.engine.prompts import (
    SOPStyle,
    get_system_prompt,
    get_instruction,
    build_fine_tune_prompt,
    get_fine_tune_generation_params,
    is_fine_tune_style,
)
from app.modules.ml.schemas import SOPResponse, TranscriptResponse, DiagramResponse, StepItemResponse
from app.core.config import settings

logger = logging.getLogger(__name__)


# helper ──────────────────────────────────────────────────────────────────────

# mapping string style ke SOPStyle enum
_STYLE_MAP = {
    "dokumen_terstruktur": SOPStyle.DOKUMEN_TERSTRUKTUR,
    "chat_wa":             SOPStyle.CHAT_WA,
    "instruksi_lisan":     SOPStyle.INSTRUKSI_LISAN,
    "diagram_mermaid":     SOPStyle.DIAGRAM_MERMAID,
    "kolom_tabel":         SOPStyle.KOLOM_TABEL,
    "fine_tune":           SOPStyle.FINE_TUNE,
}


# format durasi detik ke string "MM:SS"
def _format_duration(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"

# end of helper ───────────────────────────────────────────────────────────────


# ml operations ───────────────────────────────────────────────────────────────

# generate SOP dari teks catatan UMKM
# - input  : sop_name (str), kategori (str), catatan (str input user),
#            style (str SOPStyle string), max_new_tokens (int), temperature (float)
# - output : SOPResponse { sop, steps, step_count, valid, generation_time_seconds }
# - error  : RuntimeError kalau model belum di-load
async def generate_sop(
    sop_name: str,
    kategori: str,
    catatan: str,
    style: str = "dokumen_terstruktur",
    max_new_tokens: int = 512,
    temperature: float = 0.7,
) -> SOPResponse:
    generator = get_sop_generator(
        model_id=settings.ML_MODEL_ID,
        adapter_id=settings.ML_ADAPTER_ID,
        hf_token=settings.HUGGINGFACE_TOKEN,
    )

    if not generator.is_loaded():
        raise RuntimeError("Model SOP belum di-load. Hit POST /api/v1/ml/load terlebih dahulu.")

    style_enum = _STYLE_MAP.get(style, SOPStyle.DOKUMEN_TERSTRUKTUR)

    t0 = time.perf_counter()

    if is_fine_tune_style(style_enum):
        # fine-tune mode: flat prompt dimasukkan sebagai user-content ke chat template
        # (BUKAN bypass chat template - gemma-2-2b-it butuh <start_of_turn>model untuk generate)
        # format: apply_chat_template([{role:user, content: build_fine_tune_prompt(...)}])
        ft_params   = get_fine_tune_generation_params()
        flat_prompt = build_fine_tune_prompt(
            f"Nama SOP    : {sop_name}\n"
            f"Bidang Usaha: {kategori}\n"
            f"Catatan     :\n{catatan}"
        )
        raw = await generator.generate(
            system_prompt="",           # kosong - system prompt sudah embedded di flat_prompt
            user_message=flat_prompt,   # full flat prompt sebagai user content
            max_new_tokens=ft_params["max_new_tokens"],
            temperature=ft_params["temperature"],
            top_p=ft_params["top_p"],
            repetition_penalty=ft_params["repetition_penalty"],
            raw_prompt=False,           # tetap pakai chat template
        )
    else:
        # default mode: chat template + custom style prompt
        system_prompt = get_system_prompt(style_enum)
        instruction   = get_instruction(style_enum)
        user_message  = (
            f"{instruction}\n\n"
            f"Nama SOP    : {sop_name}\n"
            f"Bidang Usaha: {kategori}\n"
            f"Catatan     :\n{catatan}"
        )
        raw = await generator.generate(
            system_prompt=system_prompt,
            user_message=user_message,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
        )

    elapsed = round(time.perf_counter() - t0, 2)

    sop_text = clean_output(raw)
    steps_raw = parse_steps_from_sop(sop_text)
    valid = validate_output(sop_text)

    steps = [StepItemResponse(**s) for s in steps_raw]

    logger.info(
        "ML service: SOP generated (%.1fs, %d steps, valid=%s)",
        elapsed, len(steps), valid,
    )

    return SOPResponse(
        sop=sop_text,
        steps=steps,
        step_count=len(steps),
        valid=valid,
        generation_time_seconds=elapsed,
    )


# transkrip file audio ke teks Bahasa Indonesia via Whisper
# - input  : audio_bytes (bytes), filename (str untuk ext hint), language (str default "id")
# - output : TranscriptResponse { transcript, duration_seconds, duration_formatted, word_count }
# - error  : RuntimeError kalau STT model belum di-load
async def transcribe_audio(
    audio_bytes: bytes,
    filename: str,
    language: str = "id",
) -> TranscriptResponse:
    stt = get_stt_engine(model_size=settings.WHISPER_MODEL_SIZE)

    if not stt.is_loaded():
        raise RuntimeError("STT model belum di-load. Hit POST /api/v1/ml/load terlebih dahulu.")

    transcript, duration = await stt.transcribe_bytes(audio_bytes=audio_bytes, filename=filename)

    return TranscriptResponse(
        transcript=transcript,
        duration_seconds=round(duration, 2),
        duration_formatted=_format_duration(duration),
        word_count=len(transcript.split()),
    )


# render mermaid diagram ke PNG dan upload ke GCS
# - input  : mermaid_text (str), user_id (str untuk path di bucket)
# - output : DiagramResponse { url, object_name, size_bytes }
async def render_diagram(mermaid_text: str, user_id: str) -> DiagramResponse:
    result = await render_and_upload(mermaid_text=mermaid_text, user_id=user_id)
    return DiagramResponse(**result)

# end of ml operations ────────────────────────────────────────────────────────

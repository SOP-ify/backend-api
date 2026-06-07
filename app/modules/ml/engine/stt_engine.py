# app/modules/ml/engine/stt_engine.py
#
# -> speech-to-text engine pakai faster-whisper
#      -> load Whisper medium model
#      -> transcribe audio file ke teks Bahasa Indonesia
# -> model di-load on-demand (lazy), bukan saat startup
# -> support mp3, mp4, wav, m4a (semua yang faster-whisper support)
# -> VAD filter aktif untuk buang bagian silent

import logging
import os
import tempfile
from typing import Optional

logger = logging.getLogger(__name__)


# stt engine ----------------------------------------------------------------------

class STTEngine:
    """
    Wrapper untuk faster-whisper STT.
    Load on-demand lewat .load(), bukan saat init.
    """

    def __init__(self, model_size: str = "medium"):
        # - model_size : "tiny", "base", "small", "medium", "large-v3"
        #                medium = recommended (balance akurasi vs speed)
        self.model_size = model_size
        self._model = None
        self._device = None
        self._compute_type = None

    # load whisper model ke memory
    # - note : GPU pakai float16, CPU pakai int8 (lebih cepat dari float32)
    def load(self) -> None:
        if self._model is not None:
            logger.info("STTEngine: model sudah loaded, skip")
            return

        logger.info(f"STTEngine: loading whisper {self.model_size}...")

        try:
            import torch
            from faster_whisper import WhisperModel

            self._device = "cuda" if torch.cuda.is_available() else "cpu"
            self._compute_type = "float16" if self._device == "cuda" else "int8"

            self._model = WhisperModel(
                self.model_size,
                device=self._device,
                compute_type=self._compute_type,
            )
            logger.info(f"STTEngine: model ready (device={self._device}, compute={self._compute_type})")

        except Exception as e:
            self._model = None
            logger.error(f"STTEngine: gagal load model - {e}")
            raise

    # unload model dari memory
    # - output : None
    def unload(self) -> None:
        if self._model is not None:
            del self._model
            self._model = None
        logger.info("STTEngine: model unloaded")

    # cek apakah model sudah di-load
    # - output : True kalau model siap dipakai
    def is_loaded(self) -> bool:
        return self._model is not None

    # transcribe file audio ke teks Bahasa Indonesia
    # - input  : audio_path (str path ke file audio), language (str default "id")
    # - output : tuple (transcript: str, duration_seconds: float)
    # - error  : RuntimeError kalau model belum di-load
    # - note   : VAD filter aktif untuk buang bagian silent otomatis
    def transcribe(self, audio_path: str, language: str = "id") -> tuple[str, float]:
        if not self.is_loaded():
            raise RuntimeError("STT model belum di-load. Panggil /api/v1/ml/load terlebih dahulu.")

        segments, info = self._model.transcribe(
            audio_path,
            language=language,
            beam_size=5,
            vad_filter=True,  # buang bagian silent
        )

        # gabungkan semua segment jadi satu teks
        transcript = " ".join(seg.text.strip() for seg in segments).strip()
        return transcript, info.duration

    # transcribe dari bytes (upload langsung dari HTTP request)
    # - input  : audio_bytes (bytes), filename (str untuk extension hint)
    # - output : tuple (transcript: str, duration_seconds: float)
    # - note   : simpan ke tempfile dulu, hapus setelah selesai
    async def transcribe_bytes(self, audio_bytes: bytes, filename: str) -> tuple[str, float]:
        ext = os.path.splitext(filename)[-1].lower() or ".mp3"

        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            return self.transcribe(tmp_path)
        finally:
            # cleanup tempfile
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

# end of stt engine ---------------------------------------------------------------


# singleton instance
_stt_engine: Optional[STTEngine] = None


# get atau inisialisasi singleton
# - input  : model_size dari config
# - output : STTEngine instance
def get_stt_engine(model_size: str = "medium") -> STTEngine:
    global _stt_engine
    if _stt_engine is None:
        _stt_engine = STTEngine(model_size=model_size)
    return _stt_engine

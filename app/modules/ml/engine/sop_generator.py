# app/modules/ml/engine/sop_generator.py
#
# -> Gemma 2 + LoRA inference engine untuk generate SOP
#      -> load()      : load base model + LoRA adapter ke GPU/CPU
#      -> unload()    : bebaskan VRAM/RAM
#      -> generate()  : inference dengan asyncio.Lock (serialisasi concurrent request)
#      -> is_loaded() : cek status model
# -> pakai 4-bit NF4 quantization di GPU (hemat ~60% VRAM)
# -> asyncio.Lock wajib karena Cloud Run concurrency=1 tidak bisa guarantee
# -> USE_TF=0 di-set sebelum import untuk cegah protobuf conflict

import os
import logging
import asyncio
import time
from typing import Optional

# ── wajib SEBELUM import transformers ──────────────────────────────────────
os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("USE_FLAX", "0")
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
# ─────────────────────────────────────────────────────────────────────────

logger = logging.getLogger(__name__)


# sop generator ───────────────────────────────────────────────────────────────

class SOPGenerator:
    """
    Wrapper Gemma 2 + LoRA untuk generate SOP.

    Load lewat .load(), bukan saat init.
    asyncio.Lock untuk serialisasi inference di environment concurrent.
    """

    def __init__(self, model_id: str, adapter_id: str, hf_token: Optional[str] = None):
        # - model_id   : HuggingFace base model (google/gemma-2-2b-it)
        # - adapter_id : LoRA adapter (iqbalreza/sopify-gemma2-2b-umkm-lora)
        # - hf_token   : HuggingFace token untuk model private
        self.model_id = model_id
        self.adapter_id = adapter_id
        self.hf_token = hf_token
        self._model = None
        self._tokenizer = None
        self._device: Optional[str] = None
        self._lock = asyncio.Lock()

    # load model ke memori
    # - input  : device (str, "cuda" untuk GPU, "cpu" untuk CPU)
    # - output : None
    # - note   : GPU pakai 4-bit NF4 + device_map={"": "cuda:0"}
    #            CPU pakai float32 + device_map="cpu"
    def load(self, device: str = "cuda") -> None:
        if self._model is not None:
            logger.info("SOPGenerator: model sudah loaded, skip")
            return

        logger.info("SOPGenerator: loading %s ke %s...", self.model_id, device)
        t0 = time.perf_counter()

        try:
            import torch
            from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
            from peft import PeftModel

            self._tokenizer = AutoTokenizer.from_pretrained(
                self.model_id,
                token=self.hf_token,
            )

            # cek apakah target device adalah GPU (bisa "cuda" atau "cuda:0", "cuda:1", dst)
            use_cuda = device.startswith("cuda")

            if use_cuda:
                if not torch.cuda.is_available():
                    logger.warning("SOPGenerator: CUDA tidak tersedia, fallback ke CPU")
                    device = "cpu"
                    use_cuda = False
                else:
                    free_vram = torch.cuda.mem_get_info(0)[0] / 1e9
                    logger.info("SOPGenerator: target device=%s | VRAM free: %.1f GB", device, free_vram)

            if use_cuda:
                bnb_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True,
                )
                base = AutoModelForCausalLM.from_pretrained(
                    self.model_id,
                    quantization_config=bnb_config,
                    device_map={"": device},   # paksa semua layer ke device yang diminta
                    token=self.hf_token,
                )
            else:
                base = AutoModelForCausalLM.from_pretrained(
                    self.model_id,
                    torch_dtype=torch.float32,
                    device_map="cpu",
                    token=self.hf_token,
                )

            self._model = PeftModel.from_pretrained(
                base,
                self.adapter_id,
                token=self.hf_token,
            )
            self._model.eval()
            self._device = device

            elapsed = round(time.perf_counter() - t0, 2)
            if use_cuda:
                gpu_idx = int(device.split(":")[1]) if ":" in device else 0
                used = (torch.cuda.get_device_properties(gpu_idx).total_memory - torch.cuda.mem_get_info(gpu_idx)[0]) / 1e9
                logger.info("SOPGenerator: loaded dalam %.1fs | VRAM dipakai: %.1f GB", elapsed, used)
            else:
                logger.info("SOPGenerator: loaded dalam %.1fs (CPU)", elapsed)

        except Exception as e:
            self._model = None
            self._tokenizer = None
            self._device = None
            logger.error("SOPGenerator: gagal load model - %s", e)
            raise

    # unload model dari memori
    # - output : None
    def unload(self) -> None:
        if self._model is not None:
            del self._model
            self._model = None
        if self._tokenizer is not None:
            del self._tokenizer
            self._tokenizer = None
        self._device = None

        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass

        import gc
        gc.collect()
        logger.info("SOPGenerator: model unloaded")

    # cek apakah model sudah di-load
    # - output : bool
    def is_loaded(self) -> bool:
        return self._model is not None

    # generate SOP dari prompt
    # - input  : system_prompt (str), user_message (str),
    #            max_new_tokens (int, default 512), temperature (float, default 0.7)
    #            top_p (float, default 1.0), repetition_penalty (float, default 1.0)
    #            raw_prompt (bool, default False)
    #            -> True  : user_message adalah full prompt flat, skip apply_chat_template
    #                        dipakai untuk FINE_TUNE style supaya format == training data
    #            -> False : pakai apply_chat_template seperti biasa
    # - output : str teks SOP yang dihasilkan model
    # - error  : RuntimeError kalau model belum di-load
    # - note   : pakai asyncio.Lock supaya hanya 1 inference berjalan di waktu yang sama
    async def generate(
        self,
        system_prompt: str,
        user_message: str,
        max_new_tokens: int  = 512,
        temperature:   float = 0.7,
        top_p:         float = 1.0,
        repetition_penalty: float = 1.0,
        raw_prompt:    bool  = False,
    ) -> str:
        if not self.is_loaded():
            raise RuntimeError("Model belum di-load. Panggil /api/v1/ml/load terlebih dahulu.")

        async with self._lock:
            return await asyncio.get_event_loop().run_in_executor(
                None,
                self._generate_sync,
                system_prompt,
                user_message,
                max_new_tokens,
                temperature,
                top_p,
                repetition_penalty,
                raw_prompt,
            )

    # sync inference (dijalankan di thread pool via run_in_executor)
    # - input  : system_prompt, user_message, max_new_tokens, temperature,
    #            top_p, repetition_penalty, raw_prompt
    # - output : str
    def _generate_sync(
        self,
        system_prompt:      str,
        user_message:       str,
        max_new_tokens:     int,
        temperature:        float,
        top_p:              float   = 1.0,
        repetition_penalty: float   = 1.0,
        raw_prompt:         bool    = False,
    ) -> str:
        import torch

        if raw_prompt:
            # fine-tune mode: user_message adalah full flat prompt, bypass chat template
            # supaya distribusi token input == saat training
            text = user_message
        else:
            # default mode: wrap dalam chat template Gemma
            # kalau system_prompt kosong (fine-tune), pakai user_message langsung sebagai content
            content = f"{system_prompt}\n\n{user_message}" if system_prompt else user_message
            chat = [{"role": "user", "content": content}]
            text = self._tokenizer.apply_chat_template(
                chat,
                tokenize=False,
                add_generation_prompt=True,
            )

        inputs = self._tokenizer(text, return_tensors="pt").to(self._device)

        # debug: log info sebelum generate
        import sys
        n_input = inputs["input_ids"].shape[1]
        print(
            f"\n[GEN DEBUG] raw_prompt={raw_prompt} | input_tokens={n_input} | "
            f"temp={temperature} | top_p={top_p} | rep_pen={repetition_penalty}\n"
            f"  prompt[:200]: {text[:200].replace(chr(10), '↵')!r}",
            file=sys.stderr, flush=True,
        )

        with torch.no_grad():
            outputs = self._model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_p=top_p,
                repetition_penalty=repetition_penalty,
                do_sample=True,
                pad_token_id=self._tokenizer.eos_token_id,
            )

        input_len = inputs["input_ids"].shape[1]
        generated = outputs[0][input_len:]

        # debug: log jumlah token yang dihasilkan dan raw output sebelum strip
        raw_decoded = self._tokenizer.decode(generated, skip_special_tokens=False)
        print(
            f"[GEN DEBUG] generated_tokens={len(generated)} | "
            f"raw_decoded[:300]: {raw_decoded[:300].replace(chr(10), '↵')!r}",
            file=sys.stderr, flush=True,
        )

        return self._tokenizer.decode(generated, skip_special_tokens=True).strip()

    # property untuk baca device yang sedang dipakai
    # - output : str ("cuda" / "cpu") atau None kalau belum di-load
    @property
    def device(self) -> Optional[str]:
        return self._device

# end of sop generator ────────────────────────────────────────────────────────


# singleton ───────────────────────────────────────────────────────────────────

_generator: Optional[SOPGenerator] = None


# get atau inisialisasi singleton SOPGenerator
# - input  : model_id, adapter_id, hf_token dari settings
# - output : SOPGenerator instance
def get_sop_generator(
    model_id: str = "google/gemma-2-2b-it",
    adapter_id: str = "iqbalreza/sopify-gemma2-2b-umkm-lora",
    hf_token: Optional[str] = None,
) -> SOPGenerator:
    global _generator
    if _generator is None:
        _generator = SOPGenerator(
            model_id=model_id,
            adapter_id=adapter_id,
            hf_token=hf_token,
        )
    return _generator

# end of singleton ────────────────────────────────────────────────────────────

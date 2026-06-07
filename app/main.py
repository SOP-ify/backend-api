# app/main.py
#
# -> entry point FastAPI app
#      -> app factory + lifespan (startup/shutdown)
#      -> startup : connect MongoDB + load ML model (kalau ML_AUTO_LOAD=True)
#      -> shutdown : unload model + close MongoDB
#      -> mount semua router : auth, user, sop_history, ml
#      -> CORS middleware
#      -> GET /health endpoint

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import connect_db, close_db
from app.modules.auth.router import router as auth_router
from app.modules.user.router import router as user_router
from app.modules.sop_history.router import router as sop_history_router
from app.modules.ml.router import router as ml_router

logger = logging.getLogger(__name__)


# lifespan ────────────────────────────────────────────────────────────────────

# lifecycle startup dan shutdown
# - startup  : connect MongoDB, load ML model kalau ML_AUTO_LOAD=True
# - shutdown : unload model, close MongoDB
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=== SOP-ify API starting up ===")

    # connect MongoDB
    await connect_db()
    logger.info("MongoDB: connected")

    # load ML model saat startup kalau dikonfigurasi
    if settings.ML_AUTO_LOAD:
        logger.info("ML_AUTO_LOAD=True: loading model...")
        try:
            import torch
            from app.modules.ml.engine.sop_generator import get_sop_generator
            from app.modules.ml.engine.stt_engine import get_stt_engine

            device = settings.CUDA_DEVICE if torch.cuda.is_available() else "cpu"
            logger.info("ML: target device = %s", device)

            # load SOP generator (Gemma 2 + LoRA)
            generator = get_sop_generator(
                model_id=settings.ML_MODEL_ID,
                adapter_id=settings.ML_ADAPTER_ID,
                hf_token=settings.HUGGINGFACE_TOKEN,
            )
            generator.load(device=device)

            # load Whisper STT
            stt = get_stt_engine(model_size=settings.WHISPER_MODEL_SIZE)
            stt.load()

            logger.info("ML: semua model berhasil di-load ke %s", device)

        except Exception as e:
            # jangan crash server kalau model gagal load
            # endpoint /ml/load masih bisa dipanggil manual
            logger.error("ML: gagal auto-load model - %s", e)
            logger.warning("ML: server tetap jalan, panggil POST /api/v1/ml/load secara manual")

    logger.info("=== SOP-ify API ready ===")
    yield

    # ── SHUTDOWN ─────────────────────────────────────────────────────────────
    logger.info("=== SOP-ify API shutting down ===")

    try:
        from app.modules.ml.engine.sop_generator import get_sop_generator
        from app.modules.ml.engine.stt_engine import get_stt_engine
        get_sop_generator().unload()
        get_stt_engine().unload()
    except Exception as e:
        logger.warning("ML: gagal unload saat shutdown - %s", e)

    await close_db()
    logger.info("=== SOP-ify API stopped ===")

# end of lifespan ─────────────────────────────────────────────────────────────


# app factory ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Backend API SOP-ify — platform generate SOP berbasis AI untuk UMKM Indonesia.",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# mount routers
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(sop_history_router)
app.include_router(ml_router)

# end of app factory ──────────────────────────────────────────────────────────


# health ──────────────────────────────────────────────────────────────────────

# GET / dan GET /health — health check untuk Cloud Run startup probe dan load balancer
# - output : { success, message, data: { status, version, model_loaded } }
# - note   : tidak butuh auth, dipakai Cloud Run untuk cek apakah container siap
@app.get("/", tags=["Health"])
@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    try:
        from app.modules.ml.engine.sop_generator import get_sop_generator
        model_loaded = get_sop_generator().is_loaded()
    except Exception:
        model_loaded = False

    from app.shared.response import success_response
    return success_response(
        message="SOP-ify API is running",
        data={
            "status": "ok",
            "version": settings.APP_VERSION,
            "model_loaded": model_loaded,
        },
    )

# end of health ───────────────────────────────────────────────────────────────

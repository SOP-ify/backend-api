# ── SOP-ify Backend API ─────────────────────────────────────────────────────
# Multi-stage Dockerfile
#
# Stage 1 (builder) : install Python deps di isolated layer
# Stage 2 (runtime) : copy hasil install, jalankan app
#
# Base image: nvidia/cuda untuk support GPU inference (Gemma 2 + Whisper)
# CUDA 12.6 → cocok dengan PyTorch 2.7.1+cu126
#
# Build:
#   docker build -t sopify-api .
#
# Run (GPU):
#   docker run --gpus all -p 8000:8000 --env-file .env sopify-api
#
# Run (CPU only):
#   docker run -p 8000:8000 --env-file .env sopify-api


# ─── STAGE 1: builder ────────────────────────────────────────────────────────

FROM nvidia/cuda:12.6.3-cudnn-runtime-ubuntu22.04 AS builder

# metadata
LABEL maintainer="SOP-ify Team"
LABEL description="SOP-ify Backend API - FastAPI + MongoDB + Gemma 2 + Whisper"

# env build
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# install Python + build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3.10-venv \
    python3-pip \
    build-essential \
    ffmpeg \
    libsndfile1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# symlink python
RUN ln -sf /usr/bin/python3.10 /usr/bin/python3 && \
    ln -sf /usr/bin/python3 /usr/bin/python

# buat virtualenv di /opt/venv
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# upgrade pip dulu
RUN pip install --upgrade pip setuptools wheel

# copy requirements dan install
WORKDIR /install
COPY requirements.txt .

# install torch dengan CUDA 12.6 index terpisah (lebih kecil dari default)
RUN pip install torch torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/cu126

# install semua deps lainnya
RUN pip install -r requirements.txt


# ─── STAGE 2: runtime ────────────────────────────────────────────────────────

FROM nvidia/cuda:12.6.3-cudnn-runtime-ubuntu22.04 AS runtime

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # paksa transformers pakai PyTorch saja (cegah protobuf conflict dari TF)
    USE_TF=0 \
    USE_FLAX=0 \
    PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python \
    TF_CPP_MIN_LOG_LEVEL=3 \
    # Cloud Run L4 GPU: paksa pakai GPU 0
    CUDA_VISIBLE_DEVICES=0

# runtime deps minimal
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3.10-venv \
    ffmpeg \
    libsndfile1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN ln -sf /usr/bin/python3.10 /usr/bin/python3 && \
    ln -sf /usr/bin/python3 /usr/bin/python

# copy virtualenv dari builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# buat non-root user
RUN groupadd -r sopify && useradd -r -g sopify -d /app sopify

# setup workdir
WORKDIR /app

# copy source code
COPY --chown=sopify:sopify app/ ./app/
COPY --chown=sopify:sopify .env.example ./.env.example

# direktori untuk model cache dan GCS offload (kalau diperlukan)
RUN mkdir -p /app/offload_folder /app/.cache/huggingface && \
    chown -R sopify:sopify /app

# jalankan sebagai non-root
USER sopify

# expose port
EXPOSE 8000

# healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# entrypoint
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--log-level", "info"]

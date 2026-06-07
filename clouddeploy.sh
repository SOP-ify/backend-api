#!/usr/bin/env bash
# clouddeploy.sh
#
# -> script deploy SOP-ify API ke Google Cloud Run + L4 GPU
# -> region: asia-southeast1 (Singapore) — L4 GPU belum tersedia di asia-southeast2 Jakarta
# -> jalankan: bash clouddeploy.sh <PROJECT_ID>

set -euo pipefail

# ── CONFIG ────────────────────────────────────────────────────────────────────

PROJECT_ID="${1:-sop-ify}"
REGION="asia-southeast1"
SERVICE_NAME="sopify-api"
IMAGE_TAG="latest"

REGISTRY="${REGION}-docker.pkg.dev/${PROJECT_ID}/sopify/${SERVICE_NAME}:${IMAGE_TAG}"

echo "=================================================="
echo "  SOP-ify Cloud Run Deploy"
echo "  Project  : ${PROJECT_ID}"
echo "  Region   : ${REGION} (GPU: L4)"
echo "  Service  : ${SERVICE_NAME}"
echo "  Image    : ${REGISTRY}"
echo "=================================================="

# ── STEP 1: Auth ──────────────────────────────────────────────────────────────

echo ""
echo "[1/5] Set project..."
gcloud config set project "${PROJECT_ID}"

# ── STEP 2: Enable APIs ───────────────────────────────────────────────────────

echo ""
echo "[2/5] Enable required APIs..."
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  --quiet

# ── STEP 3: Create Artifact Registry repo (kalau belum ada) ──────────────────

echo ""
echo "[3/5] Create Artifact Registry repository (jika belum ada)..."
gcloud artifacts repositories create sopify \
  --repository-format=docker \
  --location="${REGION}" \
  --description="SOP-ify Docker images" \
  --quiet 2>/dev/null || echo "Repo sudah ada, lanjut..."

# ── STEP 4: Build & Push image ────────────────────────────────────────────────

echo ""
echo "[4/5] Build dan push Docker image..."
gcloud builds submit \
  --tag="${REGISTRY}" \
  --timeout=30m \
  --quiet

# ── STEP 5: Deploy ke Cloud Run ───────────────────────────────────────────────

echo ""
echo "[5/5] Deploy ke Cloud Run dengan GPU L4..."

# load env vars dari .env untuk di-pass ke Cloud Run
# NOTE: untuk production, pakai Secret Manager bukan --set-env-vars
if [ -f ".env" ]; then
  ENV_VARS=$(grep -v '^#' .env | grep -v '^$' | tr '\n' ',' | sed 's/,$//')
  ENV_FLAGS="--set-env-vars=${ENV_VARS}"
else
  echo "WARNING: .env tidak ditemukan, pastikan env vars sudah di-set manual"
  ENV_FLAGS=""
fi

gcloud run deploy "${SERVICE_NAME}" \
  --image="${REGISTRY}" \
  --region="${REGION}" \
  --gpu=1 \
  --gpu-type=nvidia-l4 \
  --memory=16Gi \
  --cpu=4 \
  --min-instances=1 \
  --max-instances=3 \
  --concurrency=1 \
  --timeout=3600 \
  --no-allow-unauthenticated \
  --execution-environment=gen2 \
  ${ENV_FLAGS} \
  --quiet

echo ""
echo "=================================================="
echo "  Deploy SELESAI!"
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" --region="${REGION}" --format="value(status.url)")
echo "  URL: ${SERVICE_URL}"
echo "  Health: ${SERVICE_URL}/health"
echo "  Docs  : ${SERVICE_URL}/docs"
echo "=================================================="

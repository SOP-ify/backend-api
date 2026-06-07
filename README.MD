# SOP-ify Backend API

Backend API untuk aplikasi mobile **SOP-ify** — platform pembuatan Standard Operating Procedure (SOP) berbasis AI untuk UMKM Indonesia.

Dibangun dengan **FastAPI**, **MongoDB Atlas**, dan arsitektur modular yang clean.

---

## Tech Stack

| Layer | Tech |
|---|---|
| Framework | FastAPI + Uvicorn |
| Database | MongoDB Atlas (Motor async driver) |
| Auth | JWT HS256 (python-jose) + Argon2 (passlib) |
| Validation | Pydantic v2 + pydantic-settings |
| ML - SOP Generator | Gemma 2 2B-it + QLoRA adapter (transformers + peft) |
| ML - Speech to Text | faster-whisper (Whisper medium) |
| ML - Diagram | mermaid.ink API → PNG |
| Storage | Google Cloud Storage (sopify-bucket, asia-southeast2) |
| Container | Docker + NVIDIA CUDA 12.6 |
| Testing | Pytest + pytest-mock (47 tests, all mocked) |

---

## Struktur Project

```
backend-api/
├── app/
│   ├── main.py                          # entry point, app factory, lifespan
│   ├── core/
│   │   ├── config.py                    # settings dari .env (pydantic-settings)
│   │   ├── database.py                  # async MongoDB client (Motor)
│   │   ├── security.py                  # password hashing & JWT utils
│   │   └── storage.py                   # Google Cloud Storage client wrapper
│   ├── modules/
│   │   ├── auth/
│   │   │   ├── router.py                # HTTP endpoints auth
│   │   │   ├── service.py               # business logic auth
│   │   │   ├── repository.py            # MongoDB queries users + blacklist
│   │   │   ├── schemas.py               # request / response models
│   │   │   └── dependencies.py          # get_current_user JWT dependency
│   │   ├── user/
│   │   │   ├── router.py                # GET/PUT /user/me, GET /user/me/summary
│   │   │   ├── service.py               # business logic profil user
│   │   │   ├── repository.py            # MongoDB queries users (partial update)
│   │   │   └── schemas.py               # UpdateProfileRequest, UserProfileResponse
│   │   ├── sop_history/
│   │   │   ├── router.py                # CRUD riwayat SOP
│   │   │   ├── service.py               # business logic riwayat
│   │   │   ├── repository.py            # MongoDB queries sop_history
│   │   │   └── schemas.py               # SaveSOPRequest, SOPHistoryDetail
│   │   └── ml/
│   │       ├── router.py                # endpoints generate SOP, STT, diagram
│   │       ├── service.py               # orkestrasi engine
│   │       ├── schemas.py               # request / response ML
│   │       └── engine/
│   │           ├── sop_generator.py     # Gemma 2 + LoRA inference
│   │           ├── stt_engine.py        # faster-whisper STT
│   │           ├── diagram_renderer.py  # mermaid.ink PNG renderer
│   │           ├── postprocessor.py     # clean + validate + parse steps
│   │           └── prompts.py           # SOPStyle enum + system prompts
│   └── shared/
│       ├── exceptions.py                # HTTP exception factories (400/401/404/409)
│       └── response.py                  # standar response envelope
├── tests/
│   ├── conftest.py                      # shared fixtures, mock data, auth helpers
│   ├── auth/
│   │   └── test_auth.py                 # 13 tests
│   ├── user/
│   │   └── test_user.py                 # 11 tests
│   ├── sop_history/
│   │   └── test_sop_history.py          # 17 tests
│   └── benchmarks/
│       ├── gen_benchmark_notebook.py    # generator script notebook
│       └── benchmark_sop_generator.ipynb  # GPU vs CPU benchmark
├── Dockerfile
├── .dockerignore
├── .env.example
└── requirements.txt
```

---

## Setup & Menjalankan Lokal

### 1. Clone dan masuk ke folder

```bash
git clone https://github.com/SOP-ify/backend-api.git
cd backend-api
```

### 2. Buat virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Konfigurasi environment

```bash
cp .env.example .env
```

Edit `.env` dengan nilai yang sesuai:

```env
MONGODB_URI="mongodb+srv://<user>:<password>@<cluster>.mongodb.net/"
MONGODB_DATABASE="sopifydb"
SECRET_KEY="<generate: python3 -c \"import secrets; print(secrets.token_hex(32))\">"
HUGGINGFACE_TOKEN="hf_xxxx"
GCS_BUCKET_NAME="sopify-bucket"
GCS_CREDENTIALS_JSON='{"type":"service_account",...}'
```

### 5. Jalankan server

```bash
uvicorn app.main:app --reload
```

API berjalan di `http://localhost:8000`  
Swagger docs: `http://localhost:8000/docs`

---

## Deploy dengan Docker

### Requirement
- Docker + NVIDIA Container Toolkit (untuk GPU)
- NVIDIA Driver ≥ 525 (CUDA 12.x)

### Build image

```bash
docker build -t sopify-api .
```

### Run dengan GPU (recommended untuk inference)

```bash
docker run --gpus all \
  -p 8000:8000 \
  --env-file .env \
  --name sopify-api \
  sopify-api
```

### Run tanpa GPU (CPU only, lambat untuk inference)

```bash
docker run \
  -p 8000:8000 \
  --env-file .env \
  --name sopify-api \
  sopify-api
```

### Docker Compose (opsional)

```yaml
# docker-compose.yml
version: "3.9"
services:
  api:
    build: .
    image: sopify-api
    ports:
      - "8000:8000"
    env_file: .env
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    restart: unless-stopped
```

```bash
docker compose up -d
```

### Catatan image

| Item | Detail |
|---|---|
| Base image | `nvidia/cuda:12.6.3-cudnn-runtime-ubuntu22.04` |
| Python | 3.10 |
| PyTorch | 2.7.1+cu126 (CUDA 12.6) |
| Build type | Multi-stage (builder + runtime) |
| User | Non-root (`sopify`) |
| Model cache | Di-download saat pertama run via HuggingFace Hub |

> **Catatan:** Model Gemma 2 + Whisper tidak di-bundle dalam image (terlalu besar). Saat container pertama start dan menerima request `/api/v1/ml/load`, model akan di-download dari HuggingFace ke cache dalam container. Pastikan `HUGGINGFACE_TOKEN` sudah di-set.

---

## API Endpoints

### Auth — `/api/v1/auth`

| Method | Endpoint | Deskripsi | Auth |
|---|---|---|---|
| `POST` | `/register` | Daftar akun baru | - |
| `POST` | `/login` | Login, dapat access token | - |
| `POST` | `/logout` | Blacklist token aktif | ✅ |
| `GET` | `/me` | Ambil profil dari token | ✅ |

### User — `/api/v1/user`

| Method | Endpoint | Deskripsi | Auth |
|---|---|---|---|
| `GET` | `/me` | Profil lengkap user | ✅ |
| `PUT` | `/me` | Update profil (full_name, username, jabatan) | ✅ |
| `GET` | `/me/summary` | Ringkasan statistik (total SOP) | ✅ |

### Riwayat SOP — `/api/v1/sop`

| Method | Endpoint | Deskripsi | Auth |
|---|---|---|---|
| `POST` | `/` | Simpan SOP ke riwayat | ✅ |
| `GET` | `/` | List riwayat SOP (paginated) | ✅ |
| `GET` | `/{id}` | Detail SOP (input catatan + output SOP) | ✅ |
| `DELETE` | `/{id}` | Hapus SOP dari riwayat | ✅ |

### ML — `/api/v1/ml`

| Method | Endpoint | Deskripsi | Auth |
|---|---|---|---|
| `POST` | `/load` | Load model ke memory (GPU/CPU) | ✅ |
| `POST` | `/unload` | Unload model (free memory) | ✅ |
| `GET` | `/status` | Status model (loaded/not, device) | ✅ |
| `POST` | `/audio-to-text` | Upload audio → transkrip teks (Whisper) | ✅ |
| `POST` | `/text-to-sop` | Teks catatan → SOP terformat (Gemma+LoRA) | ✅ |
| `POST` | `/diagram-to-png` | Mermaid string → upload PNG ke GCS | ✅ |

---

## Response Format

Semua endpoint menggunakan envelope yang konsisten:

```json
{
  "success": true,
  "message": "pesan",
  "data": { ... }
}
```

Error:
```json
{
  "success": false,
  "detail": "pesan error"
}
```

---

## ML Pipeline

### Generate SOP dari Teks

```
POST /ml/text-to-sop
  catatan (teks UMKM) + sop_name + kategori + style
    → Gemma 2 2B + LoRA adapter
    → postprocess + validate
    → parse steps (no, judul, deskripsi, pic, durasi)
    → { sop, steps, step_count, generation_time_seconds }
```

### Generate SOP dari Audio

```
POST /ml/audio-to-text
  audio file (mp3/wav/m4a/webm)
    → faster-whisper medium
    → { transcript, duration_formatted, word_count }

POST /ml/text-to-sop
  transcript → SOP
```

### Generate Diagram

```
POST /ml/diagram-to-png
  mermaid_text
    → mermaid.ink API → PNG bytes
    → upload ke GCS sopify-bucket
    → { url, object_name, size_bytes }
```

### SOPStyle Options

| Style | Output |
|---|---|
| `dokumen_terstruktur` | SOP formal 7 seksi (default) |
| `chat_wa` | Format pesan WhatsApp |
| `instruksi_lisan` | Gaya supervisor ke karyawan |
| `diagram_mermaid` | Flowchart Mermaid |
| `kolom_tabel` | Tabel markdown |

---

## Riwayat SOP — Data Model

Input dan output tersimpan dalam **satu dokumen** yang terhubung:

```json
{
  "id": "...",
  "user_id": "...",
  "sop_name": "SOP Pelayanan Kasir",
  "kategori": "Retail",
  "catatan": "input teks dari user...",
  "sop": "## SOP: Pelayanan Kasir\n...",
  "style": "dokumen_terstruktur",
  "steps": [
    { "no": 1, "judul": "Sambut Pelanggan", "deskripsi": "...", "pic": "Kasir", "durasi": "1 menit" }
  ],
  "step_count": 6,
  "generation_time_seconds": 4.27,
  "created_at": "2026-06-05T04:19:00+00:00"
}
```

---

## Menjalankan Tests

```bash
pytest tests/ -v
```

```
47 passed — tidak butuh koneksi DB nyata (semua query di-mock)
```

| Modul | Tests |
|---|---|
| `auth` | 13 — register, login, logout, JWT |
| `user` | 11 — get profile, update (validasi jabatan/username), summary |
| `sop_history` | 17 — save, list, detail, delete, pagination |
| `main + jwt` | 6 — health check, flow |

---

## Benchmark (GPU vs CPU)

Notebook benchmark tersedia di [`tests/benchmarks/`](tests/benchmarks/):

```bash
# generate notebook
python3 tests/benchmarks/gen_benchmark_notebook.py

# buka di Jupyter
jupyter notebook tests/benchmarks/benchmark_sop_generator.ipynb
```

Notebook menjalankan 5 SOPStyle × 3 prompt × 2 device = **30 runs** dan menghasilkan tabel perbandingan waktu + kualitas GPU vs CPU.

---

## Security

- Password di-hash dengan **Argon2** (memory-hard, tahan brute force)
- Token menggunakan **JWT HS256**, expiry 30 hari
- Logout menggunakan **token blacklist** di MongoDB dengan TTL index (auto-purge)
- Login aman dari **timing attack** dengan dummy verify saat email tidak ditemukan
- Semua endpoint ML dan user butuh **Bearer token** yang valid
- GCS diagram path per-user: `diagrams/{user_id}/{uuid}.png`

---

## MongoDB Collections

| Collection | Isi |
|---|---|
| `users` | Dokumen user (profil, hashed password) |
| `token_blacklist` | Token yang sudah di-logout (TTL auto-purge) |
| `sop_history` | Riwayat SOP per user (input + output) |

### Indexes

```
users.email                           → unique index
users.username                        → unique sparse index
sop_history.(user_id + created_at)    → compound index (list paginated)
token_blacklist.expires_at            → TTL index (auto-delete expired tokens)
```

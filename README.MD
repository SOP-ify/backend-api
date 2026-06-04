# SOP-ify Backend API

Backend API untuk aplikasi mobile **SOP-ify** — platform pembuatan Standard Operating Procedure berbasis AI.

Dibangun dengan **FastAPI**, **MongoDB Atlas**, dan arsitektur modular yang clean.

---

## Tech Stack

| Layer | Tech |
|---|---|
| Framework | FastAPI |
| Database | MongoDB Atlas (Motor async driver) |
| Auth | JWT (python-jose) + Argon2 (passlib) |
| Validation | Pydantic v2 + pydantic-settings |
| Server | Uvicorn |
| Testing | Pytest + pytest-mock |

---

## Struktur Project

```
backend-api/
├── app/
│   ├── main.py                        # entry point, app factory, lifespan
│   ├── core/
│   │   ├── config.py                  # settings dari .env (pydantic-settings)
│   │   ├── database.py                # async MongoDB client (Motor)
│   │   └── security.py                # password hashing & JWT utils
│   ├── modules/
│   │   └── auth/
│   │       ├── router.py              # HTTP endpoints
│   │       ├── service.py             # business logic
│   │       ├── repository.py          # MongoDB queries
│   │       ├── schemas.py             # request / response models
│   │       └── dependencies.py        # get_current_user dependency
│   └── shared/
│       ├── exceptions.py              # HTTP exception factories
│       └── response.py                # standar response envelope
├── tests/
│   ├── conftest.py                    # mock DB fixtures
│   └── auth/
│       └── test_auth.py               # auth test suite
├── .env                               # environment variables (tidak di-commit)
├── .env.example                       # template env
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

Isi `.env` dengan nilai yang sesuai:

```env
MONGODB_URI="mongodb+srv://<user>:<password>@<cluster>.mongodb.net/?appName=<app>"
MONGODB_DATABASE="sopifydb"
SECRET_KEY="ganti-dengan-secret-key-minimal-32-karakter"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=43200
```

> Generate SECRET_KEY: `python3 -c "import secrets; print(secrets.token_hex(32))"`

### 5. Jalankan server

```bash
uvicorn app.main:app --reload
```

API akan berjalan di `http://localhost:8000`

Swagger docs: `http://localhost:8000/docs`

---

## Auth Endpoints

Base URL: `/api/v1/auth`

| Method | Endpoint | Deskripsi | Auth |
|---|---|---|---|
| `POST` | `/register` | Daftar akun baru | - |
| `POST` | `/login` | Login, dapat access token | - |
| `POST` | `/logout` | Blacklist token aktif | ✅ |
| `GET` | `/me` | Ambil profil user | ✅ |
| `POST` | `/forgot-password` | Request link reset password | - |
| `POST` | `/reset-password` | Update password baru | - |

### Response Format

Semua endpoint return envelope yang konsisten:

```json
{
  "success": true,
  "message": "pesan",
  "data": { ... }
}
```

### Contoh Register

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Tita Sari",
    "email": "tita@sopify.com",
    "phone_number": "081234567890",
    "password": "SecurePass123",
    "agree_to_terms": true
  }'
```

### Contoh Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "tita@sopify.com",
    "password": "SecurePass123"
  }'
```

### Contoh Request dengan Token

```bash
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer <access_token>"
```

---

## Menjalankan Tests

```bash
pytest tests/ -v
```

Test tidak memerlukan koneksi MongoDB nyata — semua query di-mock.

---

## Security

- Password di-hash dengan **Argon2** (memory-hard, tahan brute force)
- Token menggunakan **JWT HS256**, expiry 30 hari
- Logout menggunakan **token blacklist** di MongoDB dengan TTL index (auto-purge)
- Login aman dari **timing attack** dengan dummy verify saat email tidak ditemukan
- Forgot password aman dari **email enumeration** — selalu return 200

---

## Modules yang Direncanakan

- `auth` — ✅ selesai
- `history` — 🔜 riwayat pembuatan SOP
- `ml` — 🔜 integrasi machine learning / AI generation

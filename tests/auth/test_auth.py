"""
tests/auth/test_auth.py

Integration tests for the Auth module endpoints.
Uses TestClient with mocked MongoDB repository to avoid real DB calls.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone

from app.main import app

client = TestClient(app, raise_server_exceptions=False)


# ── Fixtures ─────────────────────────────────────────────────────────────────

MOCK_USER = {
    "id": "507f1f77bcf86cd799439011",
    "full_name": "Tita Sari",
    "email": "tita@sopify.com",
    "phone_number": "081234567890",
    "hashed_password": "$argon2id$v=19$m=65536,t=3,p=4$dummyhashfortest",
    "is_active": True,
    "created_at": datetime.now(timezone.utc).isoformat(),
    "updated_at": datetime.now(timezone.utc).isoformat(),
}

VALID_REGISTER_PAYLOAD = {
    "full_name": "Tita Sari",
    "email": "newtita@sopify.com",
    "phone_number": "081234567890",
    "password": "SecurePass123",
    "agree_to_terms": True,
}

VALID_LOGIN_PAYLOAD = {
    "email": "tita@sopify.com",
    "password": "SecurePass123",
}


# ── Register Tests ────────────────────────────────────────────────────────────

class TestRegister:
    def test_register_success(self):
        """Registrasi dengan data valid harus berhasil (201)."""
        with (
            patch(
                "app.modules.auth.repository.find_user_by_email",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "app.modules.auth.repository.create_user",
                new=AsyncMock(return_value=MOCK_USER),
            ),
        ):
            response = client.post("/api/v1/auth/register", json=VALID_REGISTER_PAYLOAD)
            assert response.status_code == 201
            body = response.json()
            assert body["success"] is True
            assert "access_token" in body["data"]
            assert body["data"]["user"]["email"] == MOCK_USER["email"]

    def test_register_duplicate_email(self):
        """Registrasi dengan email yang sudah terdaftar harus gagal (409)."""
        with patch(
            "app.modules.auth.repository.find_user_by_email",
            new=AsyncMock(return_value=MOCK_USER),
        ):
            response = client.post("/api/v1/auth/register", json=VALID_REGISTER_PAYLOAD)
            assert response.status_code == 409
            assert "sudah terdaftar" in response.json()["detail"]

    def test_register_short_password(self):
        """Password kurang dari 8 karakter harus ditolak (422)."""
        payload = {**VALID_REGISTER_PAYLOAD, "password": "short"}
        response = client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 422

    def test_register_invalid_email(self):
        """Email tidak valid harus ditolak (422)."""
        payload = {**VALID_REGISTER_PAYLOAD, "email": "bukan-email"}
        response = client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 422

    def test_register_without_agreeing_to_terms(self):
        """Tidak setuju syarat & ketentuan harus ditolak (422)."""
        payload = {**VALID_REGISTER_PAYLOAD, "agree_to_terms": False}
        response = client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 422


# ── Login Tests ───────────────────────────────────────────────────────────────

class TestLogin:
    def test_login_success(self):
        """Login dengan kredensial valid harus berhasil (200)."""
        from app.core.security import hash_password
        hashed = hash_password("SecurePass123")
        user_with_hash = {**MOCK_USER, "hashed_password": hashed}

        with (
            patch(
                "app.modules.auth.repository.find_user_by_email",
                new=AsyncMock(return_value=user_with_hash),
            ),
        ):
            response = client.post("/api/v1/auth/login", json=VALID_LOGIN_PAYLOAD)
            assert response.status_code == 200
            body = response.json()
            assert body["success"] is True
            assert "access_token" in body["data"]

    def test_login_wrong_password(self):
        """Login dengan password salah harus gagal (401)."""
        from app.core.security import hash_password
        hashed = hash_password("CorrectPassword")
        user_with_hash = {**MOCK_USER, "hashed_password": hashed}

        with patch(
            "app.modules.auth.repository.find_user_by_email",
            new=AsyncMock(return_value=user_with_hash),
        ):
            payload = {**VALID_LOGIN_PAYLOAD, "password": "WrongPassword"}
            response = client.post("/api/v1/auth/login", json=payload)
            assert response.status_code == 401

    def test_login_user_not_found(self):
        """Login dengan email tidak terdaftar harus gagal (401)."""
        with patch(
            "app.modules.auth.repository.find_user_by_email",
            new=AsyncMock(return_value=None),
        ):
            response = client.post("/api/v1/auth/login", json=VALID_LOGIN_PAYLOAD)
            assert response.status_code == 401


# ── Protected Route Tests ─────────────────────────────────────────────────────

class TestProtectedRoutes:
    def _get_valid_token(self) -> str:
        """Helper to generate a real JWT for testing."""
        from app.core.security import create_access_token
        import uuid
        return create_access_token(
            data={"sub": MOCK_USER["id"], "jti": str(uuid.uuid4())}
        )

    def test_get_profile_with_valid_token(self):
        """GET /me dengan token valid harus berhasil (200)."""
        token = self._get_valid_token()
        with (
            patch(
                "app.modules.auth.repository.is_token_blacklisted",
                new=AsyncMock(return_value=False),
            ),
            patch(
                "app.modules.auth.repository.find_user_by_id",
                new=AsyncMock(return_value=MOCK_USER),
            ),
        ):
            response = client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200
            assert response.json()["data"]["email"] == MOCK_USER["email"]

    def test_get_profile_without_token(self):
        """GET /me tanpa token harus ditolak (401)."""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401

    def test_get_profile_with_invalid_token(self):
        """GET /me dengan token palsu harus ditolak (401)."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer token-palsu-banget"},
        )
        assert response.status_code == 401

    def test_logout_with_valid_token(self):
        """Logout dengan token valid harus berhasil (200)."""
        token = self._get_valid_token()
        with (
            patch(
                "app.modules.auth.repository.is_token_blacklisted",
                new=AsyncMock(return_value=False),
            ),
            patch(
                "app.modules.auth.repository.find_user_by_id",
                new=AsyncMock(return_value=MOCK_USER),
            ),
            patch(
                "app.modules.auth.repository.blacklist_token",
                new=AsyncMock(return_value=None),
            ),
        ):
            response = client.post(
                "/api/v1/auth/logout",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200
            assert response.json()["message"] == "Logout berhasil"


# ── Forgot Password Tests ─────────────────────────────────────────────────────

class TestForgotPassword:
    def test_forgot_password_existing_email(self):
        """Forgot password dengan email terdaftar harus berhasil."""
        with patch(
            "app.modules.auth.repository.find_user_by_email",
            new=AsyncMock(return_value=MOCK_USER),
        ):
            response = client.post(
                "/api/v1/auth/forgot-password",
                json={"email": MOCK_USER["email"]},
            )
            assert response.status_code == 200
            assert response.json()["success"] is True

    def test_forgot_password_non_existing_email(self):
        """Forgot password dengan email tidak terdaftar TETAP harus sukses (anti-enumeration)."""
        with patch(
            "app.modules.auth.repository.find_user_by_email",
            new=AsyncMock(return_value=None),
        ):
            response = client.post(
                "/api/v1/auth/forgot-password",
                json={"email": "notexist@sopify.com"},
            )
            assert response.status_code == 200
            assert response.json()["success"] is True


# ── Health Check ──────────────────────────────────────────────────────────────

def test_health_check():
    """Root health check endpoint harus mengembalikan 200."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["success"] is True

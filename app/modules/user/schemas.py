# app/modules/user/schemas.py
#
# -> request dan response schema untuk user module
#      -> UpdateProfileRequest  : partial update profil user
#      -> UserProfileResponse   : profil lengkap user
#      -> UserSummaryResponse   : ringkasan statistik user

from pydantic import BaseModel, field_validator
from typing import Optional
import re


# request schemas ─────────────────────────────────────────────────────────────

# schema untuk PUT /user/me
# - semua field optional (partial update)
# - jabatan bisa diupdate bebas (string, max 100 char)
# - username harus unik, alphanum + underscore, 3-30 char
class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = None
    username: Optional[str] = None
    jabatan: Optional[str] = None

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if not v:
            raise ValueError("Nama lengkap tidak boleh kosong")
        if len(v) < 2:
            raise ValueError("Nama lengkap minimal 2 karakter")
        if len(v) > 100:
            raise ValueError("Nama lengkap maksimal 100 karakter")
        return v

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip().lower()
        if not v:
            raise ValueError("Username tidak boleh kosong")
        if len(v) < 3:
            raise ValueError("Username minimal 3 karakter")
        if len(v) > 30:
            raise ValueError("Username maksimal 30 karakter")
        if not re.match(r"^[a-z0-9_]+$", v):
            raise ValueError("Username hanya boleh huruf kecil, angka, dan underscore")
        return v

    @field_validator("jabatan")
    @classmethod
    def validate_jabatan(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if len(v) > 100:
            raise ValueError("Jabatan maksimal 100 karakter")
        return v

# end of request schemas ──────────────────────────────────────────────────────


# response schemas ────────────────────────────────────────────────────────────

# profil lengkap user
# - fields  : id, full_name, email, phone_number, username, jabatan, is_active, created_at
class UserProfileResponse(BaseModel):
    id: str
    full_name: str
    email: str
    phone_number: Optional[str] = None
    username: Optional[str] = None
    jabatan: Optional[str] = None
    is_active: bool
    created_at: str


# ringkasan statistik user
# - fields  : user_id, total_sop (total SOP yang pernah dibuat)
class UserSummaryResponse(BaseModel):
    user_id: str
    total_sop: int

# end of response schemas ─────────────────────────────────────────────────────

# app/modules/auth/schemas.py
#
# -> definisi semua kontrak request dan response untuk auth
#      -> request schemas  : RegisterRequest, LoginRequest, ForgotPasswordRequest,
#                            ResetPasswordRequest, RefreshTokenRequest
#      -> response schemas : UserPublicResponse, TokenResponse, RegisterResponse
# -> validasi input dilakukan di sini pakai pydantic field_validator

from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
import re


# request schemas -----------------------------------------------------------------

# schema untuk POST /auth/register
# - fields  : full_name (str), email (EmailStr), phone_number (str | None),
#             password (str min 8 char), agree_to_terms (bool harus True)
# - validasi : nama min 2 char, password min 8 char, format HP Indonesia, terms wajib disetujui
class RegisterRequest(BaseModel):
    full_name: str
    email: EmailStr
    phone_number: Optional[str] = None
    password: str
    agree_to_terms: bool

    @field_validator("full_name")
    @classmethod
    def full_name_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Nama lengkap tidak boleh kosong")
        if len(v.strip()) < 2:
            raise ValueError("Nama lengkap minimal 2 karakter")
        return v.strip()

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password minimal 8 karakter")
        return v

    @field_validator("phone_number")
    @classmethod
    def phone_format(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v.strip() == "":
            return None
        # format nomor HP Indonesia: +62xxx / 62xxx / 0xxx, panjang 8-12 digit setelah prefix
        cleaned = re.sub(r"[\s\-\(\)]", "", v)
        if not re.match(r"^(\+62|62|0)[0-9]{8,12}$", cleaned):
            raise ValueError("Format nomor telepon tidak valid")
        return cleaned

    @field_validator("agree_to_terms")
    @classmethod
    def must_agree_to_terms(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Anda harus menyetujui syarat dan ketentuan")
        return v


# schema untuk POST /auth/login
class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = False


# schema untuk POST /auth/forgot-password
class ForgotPasswordRequest(BaseModel):
    email: EmailStr


# schema untuk POST /auth/reset-password
# - fields  : token (str JWT reset), new_password (str min 8 char)
class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password minimal 8 karakter")
        return v


# schema untuk POST /auth/refresh
class RefreshTokenRequest(BaseModel):
    refresh_token: str

# end of request schemas ----------------------------------------------------------


# response schemas ----------------------------------------------------------------

# Balikin data user
# - fields  : id, full_name, email, phone_number, is_active, created_at
class UserPublicResponse(BaseModel):
    id: str
    full_name: str
    email: str
    phone_number: Optional[str] = None
    is_active: bool
    created_at: str


# response setelah login berhasil
# - fields  : access_token, token_type, expires_in (detik), user: UserPublicResponse
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserPublicResponse


# response setelah register berhasil (sama shape-nya dengan TokenResponse)
# - fields  : user: UserPublicResponse, access_token, token_type, expires_in
class RegisterResponse(BaseModel):
    user: UserPublicResponse
    access_token: str
    token_type: str = "bearer"
    expires_in: int

# end of response schemas ---------------------------------------------------------

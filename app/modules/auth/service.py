# app/modules/auth/service.py
#
# -> handling business logic untuk auth
#      -> register user baru
#      -> login user
#      -> logout (blacklist token)
#      -> ambil profil user
#      -> forgot password
#      -> reset password
# -> orkestrasi antara schemas, repository, sama security utils

from datetime import datetime, timedelta, timezone
from jose import JWTError
import uuid

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token,
)
from app.core.config import settings
from app.modules.auth import repository
from app.modules.auth.schemas import (
    RegisterRequest,
    LoginRequest,
    UserPublicResponse,
    TokenResponse,
    RegisterResponse,
)
from app.shared.exceptions import (
    unauthorized_exception,
    conflict_exception,
    bad_request_exception,
    not_found_exception,
)


# helper --------------------------------------------------------------------------

# balikin UserPublicResponse dari raw dict MongoDB
# - input  : user_doc (dict hasil query MongoDB)
# - output : UserPublicResponse { id, full_name, email, phone_number, is_active, created_at }
def _build_user_public(user_doc: dict) -> UserPublicResponse:
    return UserPublicResponse(
        id=user_doc["id"],
        full_name=user_doc["full_name"],
        email=user_doc["email"],
        phone_number=user_doc.get("phone_number"),
        is_active=user_doc.get("is_active", True),
        created_at=user_doc["created_at"],
    )


# buat JWT token terus dikemas bareng data user
# - input  : user_doc (dict hasil query MongoDB)
# - output : dict { access_token, token_type, expires_in, user: UserPublicResponse }
def _build_token_response(user_doc: dict) -> dict:
    expires_in_seconds = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    jti = str(uuid.uuid4())

    token = create_access_token(
        data={"sub": user_doc["id"], "jti": jti},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": expires_in_seconds,
        "user": _build_user_public(user_doc),
    }

# end of helper ------------------------------------------------------------------


# auth operations -----------------------------------------------------------------

# register user baru ke MongoDB
# - input  : payload RegisterRequest { full_name, email, phone_number, password, agree_to_terms }
# - output : RegisterResponse { user, access_token, token_type, expires_in }
# - error  : 409 kalau email sudah terdaftar
async def register_user(payload: RegisterRequest) -> RegisterResponse:
    existing = await repository.find_user_by_email(payload.email)
    if existing:
        raise conflict_exception("Email sudah terdaftar")

    hashed = hash_password(payload.password)
    user_doc = await repository.create_user(
        full_name=payload.full_name,
        email=payload.email,
        hashed_password=hashed,
        phone_number=payload.phone_number,
    )

    token_data = _build_token_response(user_doc)
    return RegisterResponse(**token_data)


# login user dan balikin JWT
# - input  : payload LoginRequest { email, password, remember_me }
# - output : TokenResponse { access_token, token_type, expires_in, user }
# - error  : 401 kalau email/password salah atau akun nonaktif
# - note   : pakai dummy verify kalau user tidak ditemukan
async def login_user(payload: LoginRequest) -> TokenResponse:
    user_doc = await repository.find_user_by_email(payload.email)

    if not user_doc:
        # dummy verify buat consume waktu yang sama
        try:
            verify_password(payload.password, hash_password("dummy-timing-guard"))
        except Exception:
            pass
        raise unauthorized_exception("Email atau password salah")

    password_ok = verify_password(payload.password, user_doc["hashed_password"])
    if not password_ok:
        raise unauthorized_exception("Email atau password salah")

    if not user_doc.get("is_active", True):
        raise unauthorized_exception("Akun Anda telah dinonaktifkan")

    token_data = _build_token_response(user_doc)
    return TokenResponse(**token_data)


# logout dengan masukin JTI token ke blacklist MongoDB
# - input  : token (str JWT aktif)
# - output : None
async def logout_user(token: str) -> None:
    try:
        payload = decode_token(token)
        jti = payload.get("jti")
        exp = payload.get("exp")

        if not jti or not exp:
            raise bad_request_exception("Token tidak memiliki JTI atau expiry")

        expires_at = datetime.fromtimestamp(exp, tz=timezone.utc)
        await repository.blacklist_token(jti=jti, expires_at=expires_at)

    except JWTError:
        # token sudah invalid, logout tetap dianggap berhasil
        pass


# ambil profil user yang sedang login
# - input  : user_id (str ObjectId)
# - output : UserPublicResponse { id, full_name, email, phone_number, is_active, created_at }
# - error  : 404 kalau user tidak ditemukan di DB
async def get_user_profile(user_id: str) -> UserPublicResponse:
    user_doc = await repository.find_user_by_id(user_id)
    if not user_doc:
        raise not_found_exception("User")
    return _build_user_public(user_doc)


# inisiasi alur forgot password - kirim reset token ke email
# - input  : email (str)
# - output : dict { message, _dev_reset_token }
# - note   : selalu return success meskipun email tidak ada
# - todo   : email service blm ada
async def forgot_password(email: str) -> dict:
    user_doc = await repository.find_user_by_email(email)

    if not user_doc:
        return {"message": "Jika email terdaftar, link reset password telah dikirim"}

    # buat token reset yang expired 15 menit
    reset_token = create_access_token(
        data={"sub": user_doc["id"], "type": "password_reset"},
        expires_delta=timedelta(minutes=15),
    )

    # todo: kirim reset_token via email di sini
    # await email_service.send_password_reset(email=email, token=reset_token)

    return {
        "message": "Jika email terdaftar, link reset password telah dikirim",
        "_dev_reset_token": reset_token,
    }


# validasi reset token lalu update password user
# - input  : token (str JWT reset), new_password (str)
# - output : dict { message }
# - error  : 400 kalau token tidak valid/expired, 404 kalau user tidak ditemukan
async def reset_password(token: str, new_password: str) -> dict:
    try:
        payload = decode_token(token)
        token_type = payload.get("type")
        user_id = payload.get("sub")

        if token_type != "password_reset" or not user_id:
            raise bad_request_exception("Token reset password tidak valid")

    except JWTError:
        raise bad_request_exception("Token reset password sudah kadaluarsa atau tidak valid")

    hashed = hash_password(new_password)
    updated = await repository.update_user_password(
        user_id=user_id, hashed_password=hashed
    )

    if not updated:
        raise not_found_exception("User")

    return {"message": "Password berhasil diperbarui"}

# end of auth operations ----------------------------------------------------------

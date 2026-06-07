# app/modules/auth/router.py
#
# -> definisi semua HTTP endpoint untuk modul auth
#      -> POST /register
#      -> POST /login
#      -> POST /logout
#      -> GET  /me
# #      -> POST /forgot-password   (nonaktif)
# #      -> POST /reset-password    (nonaktif)
# -> layer ini hanya handle HTTP (request in, response out)

from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.modules.auth import service
from app.modules.auth.schemas import (
    RegisterRequest,
    LoginRequest,
    # ForgotPasswordRequest,
    # ResetPasswordRequest,
    RegisterResponse,
    TokenResponse,
    UserPublicResponse,
)
from app.modules.auth.dependencies import get_current_user
from app.shared.response import success_response

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

_bearer_scheme = HTTPBearer(auto_error=False)


# endpoints -----------------------------------------------------------------------

# POST /register
# - input  : RegisterRequest { full_name, email, phone_number, password, agree_to_terms }
# - output : { success, message, data: RegisterResponse }
# - error  : 409 email duplikat, 422 validasi gagal
@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    summary="Daftar Akun Baru",
    description="Mendaftarkan pengguna baru",
)
async def register(payload: RegisterRequest) -> dict:
    result = await service.register_user(payload)
    return success_response(
        message="Registrasi berhasil",
        data=result.model_dump(),
    )


# POST /login - login dan dapat JWT
# - input  : LoginRequest { email, password, remember_me }
# - output : { success, message, data: TokenResponse }
# - error  : 401 kredensial salah
@router.post(
    "/login",
    status_code=status.HTTP_200_OK,
    summary="Login",
    description="Login menggunakan email dan password. Mengembalikan access token.",
)
async def login(payload: LoginRequest) -> dict:
    result = await service.login_user(payload)
    return success_response(
        message="Login berhasil",
        data=result.model_dump(),
    )


# POST /logout - blacklist token yang aktif
# - input  : Authorization header Bearer token (wajib)
# - output : { success, message }
# - note   : butuh token valid via get_current_user dependency
@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Logout",
    description="Menghapus token akses",
)
async def logout(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    current_user: dict = Depends(get_current_user),
) -> dict:
    if credentials:
        await service.logout_user(token=credentials.credentials)

    return success_response(message="Logout berhasil")


# GET /me - ambil profil user yang sedang login
# - input  : Authorization header Bearer token (wajib)
# - output : { success, message, data: UserPublicResponse }
# - error  : 401 kalau tidak ada token atau token invalid
@router.get(
    "/me",
    status_code=status.HTTP_200_OK,
    summary="Profil Pengguna",
    description="Mengambil data profil pengguna yang sedang login.",
)
async def get_my_profile(current_user: dict = Depends(get_current_user)) -> dict:
    profile = await service.get_user_profile(user_id=current_user["id"])
    return success_response(
        message="Profil berhasil diambil",
        data=profile.model_dump(),
    )


# # POST /forgot-password - request link reset password
# # - input  : ForgotPasswordRequest { email }
# # - output : { success, message, data: { _dev_reset_token } }
# # - note   : selalu return 200 meskipun email tidak ada
# @router.post(
#     "/forgot-password",
#     status_code=status.HTTP_200_OK,
#     summary="Lupa Password",
#     description="Meminta link reset password dikirim ke email.",
# )
# async def forgot_password(payload: ForgotPasswordRequest) -> dict:
#     result = await service.forgot_password(email=payload.email)
#     return success_response(
#         message=result["message"],
#         data={"_dev_reset_token": result.get("_dev_reset_token")},
#     )


# # POST /reset-password - update password pakai reset token
# # - input  : ResetPasswordRequest { token, new_password }
# # - output : { success, message }
# # - error  : 400 kalau token invalid/expired
# @router.post(
#     "/reset-password",
#     status_code=status.HTTP_200_OK,
#     summary="Reset Password",
#     description="Memperbarui password menggunakan token reset yang diterima via email.",
# )
# async def reset_password(payload: ResetPasswordRequest) -> dict:
#     result = await service.reset_password(
#         token=payload.token,
#         new_password=payload.new_password,
#     )
#     return success_response(message=result["message"])

# end of endpoints ----------------------------------------------------------------

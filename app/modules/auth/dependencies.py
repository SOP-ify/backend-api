# app/modules/auth/dependencies.py
#
# -> dependency autentikasi
#      -> get_current_user dipakai di endpoint yang butuh user login
# -> ekstrak Bearer token dari Authorization header
# -> validasi token, cek blacklist, fetch user dari DB
# -> kalau valid, return user document ke endpoint yang memakainya

from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError

from app.core.security import decode_token
from app.modules.auth import repository
from app.shared.exceptions import unauthorized_exception

_bearer_scheme = HTTPBearer(auto_error=False)


# dependencies --------------------------------------------------------------------

# validate token dan return user aktif
# - input  : credentials (HTTPAuthorizationCredentials dari Authorization header)
# - output : user document (dict) kalau token valid
# - error  : 401 kalau:
#              -> tidak ada token
#              -> token malformed / expired
#              -> JTI ada di blacklist (sudah logout)
#              -> user tidak ditemukan di DB
#              -> akun nonaktif
# - pemakaian : current_user: dict = Depends(get_current_user)
async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> dict:
    if not credentials:
        raise unauthorized_exception("Token tidak ditemukan. Silakan login terlebih dahulu")

    token = credentials.credentials

    try:
        payload = decode_token(token)
        user_id: str | None = payload.get("sub")
        jti: str | None = payload.get("jti")

        if not user_id:
            raise unauthorized_exception()

    except JWTError:
        raise unauthorized_exception()

    # cek blacklist - kalau JTI ada di sana berarti token sudah di-logout
    if jti and await repository.is_token_blacklisted(jti):
        raise unauthorized_exception("Token sudah tidak berlaku. Silakan login kembali")

    # fetch user dari DB
    user = await repository.find_user_by_id(user_id)
    if not user:
        raise unauthorized_exception("Akun tidak ditemukan")

    if not user.get("is_active", True):
        raise unauthorized_exception("Akun Anda telah dinonaktifkan")

    return user

# end of dependencies -------------------------------------------------------------

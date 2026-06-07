# app/core/security.py

# -> utility password hashing dan JWT management
#      -> password hashing : Argon2 via passlib 
#      -> JWT encoding     : HS256 via python-jose

from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from jose import jwt, JWTError
from app.core.config import settings

# context passlib Argon2 
_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


# password hashing ----------------------------------------------------------------

# hash password
def hash_password(plain_password: str) -> str:
    return _pwd_context.hash(plain_password)


# verifikasi password
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _pwd_context.verify(plain_password, hashed_password)

# end of password hashing ---------------------------------------------------------


# jwt management ------------------------------------------------------------------

# buat JWT access token 
# - input  : data (dict, harus ada key 'sub' = user_id dan 'jti' = uuid),
#            expires_delta (timedelta | None, default ke ACCESS_TOKEN_EXPIRE_MINUTES)
# - output : encoded JWT string (HS256)
def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta
        if expires_delta
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


# decode dan validasi JWT token
# - input  : token (str JWT)
# - output : payload dict { sub, jti, exp, iat, ... }
# - error  : JWTError kalau token invalid, malformed, atau expired
def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


# ekstrak 'sub' (user_id) dari JWT
# - input  : token (str JWT)
# - output : user_id (str) kalau valid, None kalau token invalid atau tidak ada 'sub'
def extract_token_subject(token: str) -> str | None:
    try:
        payload = decode_token(token)
        return payload.get("sub")
    except JWTError:
        return None

# end of jwt management -----------------------------------------------------------

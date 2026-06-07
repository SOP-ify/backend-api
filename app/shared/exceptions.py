# app/shared/exceptions.py
from fastapi import HTTPException, status


# exception factories -------------------------------------------------------------

# 401 
# - input  : detail (str, default "Token tidak valid atau sudah kedaluwarsa")
def unauthorized_exception(detail: str = "Token tidak valid atau sudah kedaluwarsa") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


# 403 
# - input  : detail (str, default "Akses ditolak")
def forbidden_exception(detail: str = "Akses ditolak") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=detail,
    )


# 404
# - input  : resource (str nama resource, contoh "User", "SOP")
def not_found_exception(resource: str = "Resource") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"{resource} tidak ditemukan",
    )


# 409
# - input  : detail (str, default "Data sudah ada")
def conflict_exception(detail: str = "Data sudah ada") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=detail,
    )


# 400
# - input  : detail (str, default "Permintaan tidak valid")
def bad_request_exception(detail: str = "Permintaan tidak valid") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=detail,
    )

# end of exception factories ------------------------------------------------------

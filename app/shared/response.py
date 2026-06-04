# app/shared/response.py

# -> semua endpoint return envelope yang sama:
#      -> { "success": bool, "message": str, "data": any }
# -> pakai success_response() atau error_response() dari sini

from typing import Any
from pydantic import BaseModel


# response model ------------------------------------------------------------------

# model envelope response
# - fields : success (bool), message (str), data (any | None)
class APIResponse(BaseModel):
    success: bool
    message: str
    data: Any = None

# end of response model -----------------------------------------------------------


# response builders ---------------------------------------------------------------

# buat success response
# - input  : message (str), data (any | None)
# - output : dict { success: True, message, data }
def success_response(message: str, data: Any = None) -> dict:
    return APIResponse(success=True, message=message, data=data).model_dump()


# buat error response
# - input  : message (str), data (any | None)
# - output : dict { success: False, message, data }
def error_response(message: str, data: Any = None) -> dict:
    return APIResponse(success=False, message=message, data=data).model_dump()

# end of response builders --------------------------------------------------------

# app/modules/ml/engine/diagram_renderer.py
#
# -> render diagram Mermaid ke PNG lalu upload ke GCS
#      -> render_to_png    : mermaid string → PNG bytes via mermaid.ink API
#      -> upload_diagram   : upload PNG ke GCS, balikin public URL
# -> mermaid.ink : free public API, tidak butuh install lokal
# -> timeout 30 detik untuk request ke mermaid.ink

import base64
import logging
from typing import Optional

import httpx

from app.core.storage import upload_bytes, make_diagram_object_name

logger = logging.getLogger(__name__)

MERMAID_INK_URL = "https://mermaid.ink/img"
REQUEST_TIMEOUT = 30.0


# rendering ───────────────────────────────────────────────────────────────────

# render mermaid string ke PNG bytes via mermaid.ink API
# - input  : mermaid_text (str, flowchart TD ... )
# - output : bytes PNG
# - error  : httpx.HTTPError kalau mermaid.ink tidak respond
#            ValueError kalau mermaid_text kosong
async def render_to_png(mermaid_text: str) -> bytes:
    if not mermaid_text.strip():
        raise ValueError("mermaid_text tidak boleh kosong")

    # encode ke base64 URL-safe (format yang dipakai mermaid.ink)
    encoded = base64.urlsafe_b64encode(mermaid_text.encode("utf-8")).decode("utf-8")
    url = f"{MERMAID_INK_URL}/{encoded}"

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        response = await client.get(url)
        response.raise_for_status()

    logger.info("DiagramRenderer: render OK (%d bytes PNG)", len(response.content))
    return response.content


# upload ke GCS dan balikin URL
# - input  : png_bytes (bytes), user_id (str untuk path di bucket)
# - output : dict { "url": str public URL, "object_name": str }
# - error  : Exception dari GCS kalau upload gagal
async def upload_diagram(png_bytes: bytes, user_id: str) -> dict:
    import asyncio

    object_name = make_diagram_object_name(user_id=user_id)

    # upload GCS dijalankan di thread pool (blocking GCS client)
    url = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: upload_bytes(data=png_bytes, object_name=object_name, content_type="image/png"),
    )

    logger.info("DiagramRenderer: uploaded ke GCS → %s", url)
    return {
        "url": url,
        "object_name": object_name,
        "size_bytes": len(png_bytes),
    }


# render + upload dalam satu langkah
# - input  : mermaid_text (str), user_id (str)
# - output : dict { "url", "object_name", "size_bytes" }
async def render_and_upload(mermaid_text: str, user_id: str) -> dict:
    png_bytes = await render_to_png(mermaid_text)
    return await upload_diagram(png_bytes=png_bytes, user_id=user_id)

# end of rendering ────────────────────────────────────────────────────────────

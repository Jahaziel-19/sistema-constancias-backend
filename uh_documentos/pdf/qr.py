from __future__ import annotations

import base64
import io
from typing import Any


def generar_qr_png_base64(payload: str, *, box_size: int = 10, border: int = 2) -> str:
    if not payload:
        return ""
    try:
        import qrcode  # type: ignore

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=box_size,
            border=border,
        )
        qr.add_data(payload)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:
        return ""


def build_qr_verification_data(*, folio: str, public_base_url: str = "") -> dict[str, str]:
    base_verif = public_base_url.rstrip("/") if public_base_url else ""
    if not base_verif:
        try:
            from django.conf import settings
            allowed = getattr(settings, "ALLOWED_HOSTS", []) or ["localhost"]
            host = allowed[0] if allowed else "localhost"
            base_verif = f"http://{host}:5173"
        except Exception:
            base_verif = "http://localhost:5173"
    verif_url = f"{base_verif}/verificar"
    qr_payload = f"{verif_url}?folio={folio}" if folio else verif_url
    qr_b64 = generar_qr_png_base64(qr_payload)
    return {
        "qr_png_base64": qr_b64,
        "url_verificacion": verif_url,
    }

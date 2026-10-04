# apps/badges/qr.py
"""
QR code generation for badges.

Encodes the public verification URL. Kept as a small module so both the
renderer and the serializer can call it without pulling in the whole
badge service layer.
"""
import io
from urllib.parse import quote

import qrcode
from django.conf import settings

from .constants import BADGE_PNG_SIZE


def verification_url(badge_id: str) -> str:
    base = getattr(
        settings, "KALRO_BADGE_VERIFY_BASE_URL",
        "https://mkulima.kalro.org/badges/verify"
    ).rstrip("/")
    return f"{base}/{quote(badge_id)}"


def make_qr_png_bytes(badge_id: str, box_size: int = 10) -> bytes:
    """Returns a PNG QR code that encodes the verification URL."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=2,
    )
    qr.add_data(verification_url(badge_id))
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
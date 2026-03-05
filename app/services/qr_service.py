"""
QR code generation service.
"""

import io
import base64
import uuid
import qrcode


def generate_qr_token() -> str:
    """Generate a cryptographically random token for QR verification."""
    return uuid.uuid4().hex


def generate_qr_code_base64(data: str) -> str:
    """Create a QR code image from *data* and return it as a base64-encoded PNG string."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1e1b4b", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")

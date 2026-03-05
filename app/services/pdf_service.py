"""
PDF generation service — produces downloadable gate-pass documents.
"""

import io
import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader


def generate_pass_pdf(gatepass, student, approver_name: str, base_url: str) -> io.BytesIO:
    """Build a professional gate-pass PDF and return the buffer."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # ── background ────────────────────────────────────────────────────────
    c.setFillColor(HexColor("#f8fafc"))
    c.rect(0, 0, width, height, fill=1, stroke=0)

    # ── header bar ────────────────────────────────────────────────────────
    c.setFillColor(HexColor("#4f46e5"))
    c.rect(0, height - 3.5 * cm, width, 3.5 * cm, fill=1, stroke=0)
    c.setFillColor(HexColor("#ffffff"))
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(width / 2, height - 2 * cm, "CAMPUS GATE PASS")
    c.setFont("Helvetica", 11)
    c.drawCentredString(width / 2, height - 2.8 * cm, "Official Authorization Document")

    # ── pass id badge ─────────────────────────────────────────────────────
    c.setFillColor(HexColor("#6366f1"))
    c.roundRect(width - 6 * cm, height - 5.5 * cm, 4.5 * cm, 1.2 * cm, 6, fill=1, stroke=0)
    c.setFillColor(HexColor("#ffffff"))
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(width - 3.75 * cm, height - 5.1 * cm, f"PASS #{gatepass.id:04d}")

    # ── status badge ──────────────────────────────────────────────────────
    status_colors = {
        "Approved": "#059669",
        "Pending": "#d97706",
        "Rejected": "#dc2626",
        "Expired": "#6b7280",
        "Cancelled": "#9ca3af",
    }
    color = status_colors.get(gatepass.status, "#6b7280")
    c.setFillColor(HexColor(color))
    c.roundRect(2 * cm, height - 5.5 * cm, 4 * cm, 1.2 * cm, 6, fill=1, stroke=0)
    c.setFillColor(HexColor("#ffffff"))
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(4 * cm, height - 5.1 * cm, gatepass.status.upper())

    # ── student information ───────────────────────────────────────────────
    y = height - 7.5 * cm
    c.setFillColor(HexColor("#1e293b"))
    c.setFont("Helvetica-Bold", 14)
    c.drawString(2 * cm, y, "Student Information")
    y -= 0.3 * cm
    c.setStrokeColor(HexColor("#e2e8f0"))
    c.setLineWidth(1)
    c.line(2 * cm, y, width - 2 * cm, y)

    y -= 1 * cm
    for label, value in [
        ("Name", student.name),
        ("Roll Number", student.roll_number),
        ("Department", student.department),
        ("Year", student.year),
    ]:
        c.setFillColor(HexColor("#64748b"))
        c.setFont("Helvetica", 10)
        c.drawString(2 * cm, y, label)
        c.setFillColor(HexColor("#1e293b"))
        c.setFont("Helvetica-Bold", 11)
        c.drawString(7 * cm, y, str(value))
        y -= 0.8 * cm

    # ── pass details ──────────────────────────────────────────────────────
    y -= 0.5 * cm
    c.setFillColor(HexColor("#1e293b"))
    c.setFont("Helvetica-Bold", 14)
    c.drawString(2 * cm, y, "Pass Details")
    y -= 0.3 * cm
    c.setStrokeColor(HexColor("#e2e8f0"))
    c.line(2 * cm, y, width - 2 * cm, y)

    y -= 1 * cm
    for label, value in [
        ("Reason", gatepass.reason[:60]),
        ("Date", gatepass.date),
        ("Out Time", gatepass.out_time),
        ("Return Time", gatepass.return_time),
        ("Approved By", approver_name or "—"),
    ]:
        c.setFillColor(HexColor("#64748b"))
        c.setFont("Helvetica", 10)
        c.drawString(2 * cm, y, label)
        c.setFillColor(HexColor("#1e293b"))
        c.setFont("Helvetica-Bold", 11)
        c.drawString(7 * cm, y, str(value))
        y -= 0.8 * cm

    # ── QR code ───────────────────────────────────────────────────────────
    if gatepass.qr_token:
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(f"{base_url}verify/{gatepass.qr_token}")
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="#1e1b4b", back_color="white")
        qr_buffer = io.BytesIO()
        qr_img.save(qr_buffer, format="PNG")
        qr_buffer.seek(0)
        qr_image = ImageReader(qr_buffer)
        qr_size = 5 * cm
        qr_x = width / 2 - qr_size / 2
        qr_y = 3 * cm
        c.setFillColor(HexColor("#ffffff"))
        c.setStrokeColor(HexColor("#e2e8f0"))
        c.roundRect(
            qr_x - 0.5 * cm, qr_y - 0.5 * cm,
            qr_size + 1 * cm, qr_size + 1.5 * cm,
            8, fill=1, stroke=1,
        )
        c.drawImage(qr_image, qr_x, qr_y, qr_size, qr_size)
        c.setFillColor(HexColor("#64748b"))
        c.setFont("Helvetica", 8)
        c.drawCentredString(width / 2, qr_y - 0.3 * cm, "Scan to verify this gate pass")

    # ── footer ────────────────────────────────────────────────────────────
    c.setFillColor(HexColor("#94a3b8"))
    c.setFont("Helvetica", 8)
    c.drawCentredString(width / 2, 1.5 * cm, "This is a computer-generated document. No signature required.")

    c.save()
    buffer.seek(0)
    return buffer

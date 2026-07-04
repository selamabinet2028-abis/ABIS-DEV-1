"""Clearance services: decisions, certificate generation (PDF + QR)."""

from __future__ import annotations

import hashlib
import hmac
import io
import json
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import connection
from django.utils import timezone
from qrcode import QRCode
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from apps.registration.models import ClearanceApplication
from apps.registration.services import transition

from .models import Certificate

Status = ClearanceApplication.Status


def generate_certificate_no() -> str:
    with connection.cursor() as cursor:
        cursor.execute("SELECT nextval('abis_certificate_no_seq')")
        (value,) = cursor.fetchone()
    return f"CERT-{timezone.now().year}-{value:06d}"


def generate_verification_no() -> str:
    """Random, non-enumerable public identifier (ADR-008)."""
    for _ in range(10):
        candidate = f"EFP-{secrets.token_hex(6).upper()}"
        if not Certificate.objects.filter(verification_no=candidate).exists():
            return candidate
    raise RuntimeError("Could not generate a unique verification number.")


# ------------------------------------------------------------- QR payload


def _qr_signature(verification_no: str, holder_name: str, issued_iso: str) -> str:
    # The name is displayed to verifiers, so it MUST be inside the signature —
    # otherwise a forged QR could pair a valid number with a different name.
    message = f"{verification_no}|{holder_name}|{issued_iso}".encode()
    return hmac.new(
        settings.ABIS_QR_SECRET.encode(), message, hashlib.sha256
    ).hexdigest()[:16]


def build_qr_payload(verification_no: str, holder_name: str, issued_iso: str) -> str:
    return json.dumps(
        {
            "v": 1,
            "no": verification_no,
            "name": holder_name,
            "issued": issued_iso,
            "sig": _qr_signature(verification_no, holder_name, issued_iso),
        },
        separators=(",", ":"),
    )


def verify_qr_payload(payload: str) -> tuple[bool, str | None]:
    """Returns (signature_valid, verification_no|None). Raises ValueError on junk."""
    data = json.loads(payload)
    if not isinstance(data, dict) or not {"no", "name", "issued"} <= set(data):
        raise ValueError("QR payload missing required fields.")
    expected = _qr_signature(data["no"], data["name"], data["issued"])
    return hmac.compare_digest(expected, data.get("sig", "")), data["no"]


# ------------------------------------------------------------- decisions


def decide(
    application: ClearanceApplication, *, decision: str, note: str = "", by=None
):
    if decision not in {"approved", "rejected"}:
        raise ValidationError("Decision must be 'approved' or 'rejected'.")
    return transition(application, decision, note=note)


# ------------------------------------------------------------- issuance


def render_certificate_pdf(certificate: Certificate) -> bytes:
    person = certificate.person
    application = certificate.application
    buffer = io.BytesIO()
    page = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    page.setFont("Helvetica-Bold", 16)
    page.drawCentredString(width / 2, height - 40 * mm, "FEDERAL POLICE COMMISSION")
    page.setFont("Helvetica-Bold", 14)
    page.drawCentredString(width / 2, height - 50 * mm, "POLICE CLEARANCE CERTIFICATE")

    page.setFont("Helvetica", 11)
    lines = [
        ("Certificate No.", certificate.certificate_no),
        ("Verification No.", certificate.verification_no),
        ("Holder", person.full_name),
        ("Person No.", person.person_no),
        ("Tracking No.", application.tracking_no),
        ("Purpose", application.purpose),
        (
            "Issued",
            (
                certificate.created_at.strftime("%Y-%m-%d")
                if certificate.created_at
                else timezone.now().strftime("%Y-%m-%d")
            ),
        ),
        ("Expires", certificate.expires_at.strftime("%Y-%m-%d")),
    ]
    y = height - 70 * mm
    for label, value in lines:
        page.drawString(30 * mm, y, f"{label}:")
        page.drawString(75 * mm, y, str(value))
        y -= 8 * mm

    page.setFont("Helvetica-Oblique", 10)
    page.drawString(
        30 * mm,
        y - 6 * mm,
        "This certifies that no criminal record was found for the holder as of the issue date.",
    )

    qr = QRCode(box_size=4, border=2)
    qr.add_data(certificate.qr_payload)
    qr.make(fit=True)
    qr_image = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    page.drawImage(ImageReader(qr_image), width - 65 * mm, 25 * mm, 40 * mm, 40 * mm)
    page.setFont("Helvetica", 8)
    page.drawString(
        width - 65 * mm, 20 * mm, f"Verify: /verify → {certificate.verification_no}"
    )

    page.showPage()
    page.save()
    return buffer.getvalue()


def issue_certificate(
    application: ClearanceApplication, *, issued_by=None
) -> Certificate:
    if application.status != Status.APPROVED:
        raise ValidationError(
            "Certificates can only be issued for approved applications."
        )
    if Certificate.objects.filter(application=application).exists():
        raise ValidationError(
            "A certificate has already been issued for this application."
        )

    issued_at = timezone.now()
    verification_no = generate_verification_no()
    certificate = Certificate.objects.create(
        application=application,
        person=application.person,
        certificate_no=generate_certificate_no(),
        verification_no=verification_no,
        qr_payload=build_qr_payload(
            verification_no, application.person.full_name, issued_at.isoformat()
        ),
        issued_by=issued_by,
        expires_at=issued_at + timedelta(days=settings.ABIS_CERT_VALIDITY_DAYS),
    )
    certificate.pdf_file.save(
        f"{certificate.certificate_no}.pdf",
        ContentFile(render_certificate_pdf(certificate)),
        save=True,
    )
    transition(application, Status.CERTIFICATE_ISSUED)
    return certificate

"""Verification services: lookup + event logging + masking."""

from __future__ import annotations

from apps.clearance.models import Certificate

from .models import VerificationEvent


def mask_name(full_name: str) -> str:
    """'Kebede Alemu Tesfaye' → 'Kebede A. T.' (first name + initials)."""
    parts = [p for p in full_name.split() if p]
    if not parts:
        return ""
    masked = [parts[0]] + [f"{p[0].upper()}." for p in parts[1:]]
    return " ".join(masked)


def verify_by_number(
    verification_no: str,
    *,
    channel: str,
    verifier_ip: str | None = None,
    api_credential=None,
) -> tuple[Certificate | None, str]:
    """Returns (certificate|None, result) and logs a VerificationEvent."""
    certificate = (
        Certificate.objects.filter(verification_no=verification_no)
        .select_related("person", "application")
        .first()
    )
    if certificate is None:
        result = VerificationEvent.Result.INVALID
    else:
        result = certificate.effective_status  # valid | revoked | expired

    VerificationEvent.objects.create(
        certificate=certificate,
        verification_no_attempted=verification_no[:40],
        channel=channel,
        result=result,
        verifier_ip=verifier_ip,
        api_credential=api_credential,
    )
    return certificate, result


def public_payload(certificate: Certificate | None, result: str) -> dict:
    """Masked response shape for portal/QR channels."""
    if certificate is None:
        return {"valid": False, "status": "invalid"}
    return {
        "valid": result == "valid",
        "status": result,
        "holder_name_masked": mask_name(certificate.person.full_name),
        "issued_at": certificate.created_at,
        "expires_at": certificate.expires_at,
    }

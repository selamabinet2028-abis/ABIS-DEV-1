"""API credential services (T-014 minimal; T-017 adds connectors/CRUD)."""

from __future__ import annotations

import hashlib
import hmac
import secrets

from .models import ApiCredential


def create_credential(*, name: str, scopes: list[str] | None = None, created_by=None):
    """Returns (credential, raw_key). The raw key is shown exactly once."""
    key_prefix = secrets.token_hex(4)
    secret = secrets.token_urlsafe(24)
    credential = ApiCredential.objects.create(
        name=name,
        key_prefix=key_prefix,
        key_hash=hashlib.sha256(secret.encode()).hexdigest(),
        scopes=scopes or [],
        created_by=created_by,
    )
    return credential, f"{key_prefix}.{secret}"


def authenticate_api_key(raw_key: str | None) -> ApiCredential | None:
    if not raw_key or "." not in raw_key:
        return None
    key_prefix, _, secret = raw_key.partition(".")
    credential = ApiCredential.objects.filter(
        key_prefix=key_prefix, is_active=True
    ).first()
    if credential is None:
        return None
    expected = hashlib.sha256(secret.encode()).hexdigest()
    if not hmac.compare_digest(expected, credential.key_hash):
        return None
    return credential

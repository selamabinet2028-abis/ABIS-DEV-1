"""Field-level encryption for biometric templates (Fernet, ADR-008).

Key comes from the ABIS_FIELD_KEY env var (see .env.example); prod fails fast
without it (config.settings.prod).
"""

from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    key = settings.ABIS_FIELD_KEY
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except (ValueError, TypeError) as exc:
        raise ImproperlyConfigured(
            "ABIS_FIELD_KEY must be a valid 32-byte urlsafe-base64 Fernet key "
            "(generate one with cryptography.fernet.Fernet.generate_key())."
        ) from exc


def encrypt_bytes(plaintext: bytes) -> bytes:
    return _fernet().encrypt(plaintext)


def decrypt_bytes(ciphertext: bytes) -> bytes:
    try:
        return _fernet().decrypt(bytes(ciphertext))
    except InvalidToken as exc:
        raise ValueError(
            "Ciphertext cannot be decrypted with the configured key."
        ) from exc

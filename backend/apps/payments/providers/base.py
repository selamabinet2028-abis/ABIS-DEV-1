"""Payment provider driver interface (golden rule: adapters + dev sandbox).

A real gateway integrates by subclassing PaymentProvider and pointing
`ABIS_PAYMENT_PROVIDERS[method]` at it; business logic never imports a
vendor SDK directly.
"""

from __future__ import annotations

import abc
import hashlib
import hmac
from functools import lru_cache
from typing import Any

from django.conf import settings
from django.utils.module_loading import import_string


class PaymentProvider(abc.ABC):
    def __init__(self, method: str):
        self.method = method

    @abc.abstractmethod
    def create_checkout(self, payment) -> dict[str, Any]:
        """Register the payment with the gateway → {gateway_ref, checkout_url}."""

    @abc.abstractmethod
    def parse_webhook(self, data: dict) -> dict[str, Any]:
        """Normalize a webhook payload → {gateway_ref, status, amount}."""

    def verify_signature(self, raw_body: bytes, signature: str | None) -> bool:
        """HMAC-SHA256 over the raw body with the provider's shared secret."""
        if not signature:
            return False
        secret = settings.ABIS_PAYMENT_WEBHOOK_SECRETS.get(self.method, "")
        expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)


@lru_cache(maxsize=8)
def get_provider(method: str) -> PaymentProvider:
    path = settings.ABIS_PAYMENT_PROVIDERS.get(method)
    if not path:
        raise KeyError(f"No payment provider configured for method '{method}'.")
    return import_string(path)(method)

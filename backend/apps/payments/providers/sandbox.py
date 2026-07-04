"""Deterministic sandbox gateway for local dev (telebirr/cbe_birr/chapa)."""

from __future__ import annotations

from typing import Any

from .base import PaymentProvider


class SandboxProvider(PaymentProvider):
    def create_checkout(self, payment) -> dict[str, Any]:
        gateway_ref = f"SBX-{self.method[:3].upper()}-{payment.id.hex[:12]}"
        return {
            "gateway_ref": gateway_ref,
            "checkout_url": f"https://sandbox.local/{self.method}/pay/{gateway_ref}",
        }

    def parse_webhook(self, data: dict) -> dict[str, Any]:
        return {
            "gateway_ref": data.get("gateway_ref", ""),
            "status": data.get("status", ""),
            "amount": data.get("amount"),
        }

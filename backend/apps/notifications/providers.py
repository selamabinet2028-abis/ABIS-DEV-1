"""SMS provider adapter (golden rule: adapters + dev mock).

A real gateway integrates by subclassing SmsProvider and pointing
`ABIS_SMS_PROVIDER` at it.
"""

from __future__ import annotations

import abc
import logging
import uuid
from functools import lru_cache

from django.conf import settings
from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)


class SmsProvider(abc.ABC):
    @abc.abstractmethod
    def send(self, to_number: str, body: str) -> str:
        """Send one SMS; returns the provider reference. Raises on failure."""


class ConsoleSmsProvider(SmsProvider):
    """Dev provider — logs the message and pretends it was delivered."""

    def send(self, to_number: str, body: str) -> str:
        reference = f"console-{uuid.uuid4().hex[:12]}"
        logger.info("SMS [%s] to %s: %s", reference, to_number, body)
        return reference


@lru_cache(maxsize=1)
def get_sms_provider() -> SmsProvider:
    return import_string(settings.ABIS_SMS_PROVIDER)()

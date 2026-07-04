"""Deterministic dev engine over GRID16 templates (T-007 preprocessing)."""

from __future__ import annotations

import numpy as np

from apps.preprocessing import services as preprocessing

from .base import MatchingEngine


class MockEngine(MatchingEngine):
    name = "mock-grid16"

    def extract(self, image_bytes: bytes) -> bytes:
        return preprocessing.extract_template(image_bytes)

    def similarity(self, probe: bytes, candidate: bytes) -> float:
        probe_vec = self._vector(probe)
        candidate_vec = self._vector(candidate)
        if probe_vec is None or candidate_vec is None:
            return 0.0
        diff = np.abs(
            probe_vec.astype(np.int16) - candidate_vec.astype(np.int16)
        ).mean()
        return round(100.0 * (1.0 - diff / 255.0), 2)

    @staticmethod
    def _vector(template: bytes) -> np.ndarray | None:
        if not template.startswith(preprocessing.TEMPLATE_PREFIX):
            return None
        payload = template[len(preprocessing.TEMPLATE_PREFIX) :]
        if len(payload) != 256:
            return None
        return np.frombuffer(payload, dtype=np.uint8)

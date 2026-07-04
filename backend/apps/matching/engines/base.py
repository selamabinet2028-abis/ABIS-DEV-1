"""MatchingEngine adapter interface (ADR-004).

A production SDK integrates by subclassing MatchingEngine and pointing the
`MATCHING_ENGINE` setting at it — business logic never imports a vendor SDK.
The contract tests in apps/matching/tests/test_engine_contract.py must pass
for every engine implementation.
"""

from __future__ import annotations

import abc
from functools import lru_cache
from typing import Any, Iterable

from django.conf import settings
from django.utils.module_loading import import_string

GalleryItem = tuple[Any, bytes]  # (opaque key, template bytes)


class MatchingEngine(abc.ABC):
    name: str = "base"

    @abc.abstractmethod
    def extract(self, image_bytes: bytes) -> bytes:
        """Image bytes → template bytes."""

    @abc.abstractmethod
    def similarity(self, probe: bytes, candidate: bytes) -> float:
        """Similarity score 0..100 (100 = identical)."""

    def verify(
        self, probe: bytes, candidate: bytes, *, threshold: float
    ) -> tuple[bool, float]:
        score = self.similarity(probe, candidate)
        return score >= threshold, score

    def identify(
        self,
        probe: bytes,
        gallery: Iterable[GalleryItem],
        *,
        threshold: float,
        top_k: int,
    ) -> list[tuple[Any, float]]:
        """Ranked (key, score) list, best first, scores >= threshold."""
        scored = [(key, self.similarity(probe, template)) for key, template in gallery]
        hits = [item for item in scored if item[1] >= threshold]
        hits.sort(key=lambda item: -item[1])
        return hits[:top_k]

    def dedup(
        self,
        probes: Iterable[bytes],
        gallery: Iterable[GalleryItem],
        *,
        threshold: float,
        top_k: int,
    ) -> list[tuple[Any, float]]:
        """Best score per gallery key across all probe templates."""
        gallery = list(gallery)
        best: dict[Any, float] = {}
        for probe in probes:
            for key, score in self.identify(
                probe, gallery, threshold=threshold, top_k=top_k
            ):
                if score > best.get(key, -1.0):
                    best[key] = score
        ranked = sorted(best.items(), key=lambda item: -item[1])
        return ranked[:top_k]


@lru_cache(maxsize=1)
def get_engine() -> MatchingEngine:
    engine_cls = import_string(settings.MATCHING_ENGINE)
    return engine_cls()

"""ADR-004 engine contract — must pass for MockEngine AND any future SDK engine."""

import pytest

from apps.matching.engines.base import get_engine

from .helpers import png_bytes


@pytest.fixture
def engine():
    return get_engine()


class TestEngineContract:
    def test_extract_is_deterministic(self, engine):
        image = png_bytes(1)
        assert engine.extract(image) == engine.extract(image)

    def test_identical_templates_score_100(self, engine):
        template = engine.extract(png_bytes(2))
        assert engine.similarity(template, template) == 100.0

    def test_different_images_score_below_identical(self, engine):
        a = engine.extract(png_bytes(3))
        b = engine.extract(png_bytes(4))
        assert engine.similarity(a, b) < 100.0

    def test_similarity_is_symmetric(self, engine):
        a = engine.extract(png_bytes(5))
        b = engine.extract(png_bytes(6))
        assert engine.similarity(a, b) == pytest.approx(engine.similarity(b, a))

    def test_verify_accepts_identical_rejects_distinct(self, engine):
        a = engine.extract(png_bytes(7))
        b = engine.extract(png_bytes(8))
        ok_same, score_same = engine.verify(a, a, threshold=80.0)
        ok_diff, score_diff = engine.verify(a, b, threshold=80.0)
        assert ok_same and score_same == 100.0
        assert not ok_diff and score_diff < 80.0

    def test_identify_ranks_best_first_and_respects_threshold(self, engine):
        probe = engine.extract(png_bytes(9))
        gallery = [
            ("identical", engine.extract(png_bytes(9))),
            ("other-1", engine.extract(png_bytes(10))),
            ("other-2", engine.extract(png_bytes(11))),
        ]
        results = engine.identify(probe, gallery, threshold=80.0, top_k=10)
        assert results[0] == ("identical", 100.0)
        assert all(score >= 80.0 for _, score in results)
        scores = [score for _, score in results]
        assert scores == sorted(scores, reverse=True)

    def test_identify_honors_top_k(self, engine):
        probe = engine.extract(png_bytes(12))
        gallery = [(f"dup-{i}", engine.extract(png_bytes(12))) for i in range(5)]
        results = engine.identify(probe, gallery, threshold=0.0, top_k=3)
        assert len(results) == 3

    def test_dedup_aggregates_best_score_per_key(self, engine):
        probes = [engine.extract(png_bytes(13)), engine.extract(png_bytes(14))]
        gallery = [
            ("match-13", engine.extract(png_bytes(13))),
            ("unrelated", engine.extract(png_bytes(15))),
        ]
        results = engine.dedup(probes, gallery, threshold=80.0, top_k=10)
        assert ("match-13", 100.0) in results
        assert all(key != "unrelated" for key, _ in results)

    def test_garbage_template_scores_zero(self, engine):
        good = engine.extract(png_bytes(16))
        assert engine.similarity(good, b"not-a-template") == 0.0

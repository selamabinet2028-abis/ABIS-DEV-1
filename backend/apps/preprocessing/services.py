"""Pre-processing: image quality scoring, template extraction, NIST-ish metadata.

The quality heuristic (contrast + Laplacian sharpness) approximates NFIQ's
1–5 scale well enough for dev; the production SDK replaces it behind the same
functions. Template format `GRID16` — 16×16 normalized grayscale — is the
deterministic feature vector the T-008 MockEngine compares.
"""

from __future__ import annotations

import hashlib
import io
from typing import Any

import cv2
import numpy as np
from PIL import Image

TEMPLATE_PREFIX = b"GRID16:"
TEMPLATE_ENGINE = "grid16-mock"
TEMPLATE_VERSION = 1


def _decode_grayscale(image_bytes: bytes) -> np.ndarray:
    array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise ValueError("Not a decodable image.")
    return image


def quality_score(image_bytes: bytes) -> int:
    """NFIQ-like heuristic score 1 (unusable) … 5 (excellent)."""
    image = _decode_grayscale(image_bytes)
    contrast = float(image.std())
    sharpness = float(cv2.Laplacian(image, cv2.CV_64F).var())

    score = 1
    if contrast > 10:
        score += 1
    if contrast > 30:
        score += 1
    if sharpness > 50:
        score += 1
    if sharpness > 300:
        score += 1
    return min(score, 5)


def extract_template(image_bytes: bytes) -> bytes:
    """Deterministic 16×16 grayscale feature grid (mock template)."""
    image = _decode_grayscale(image_bytes)
    resized = cv2.resize(image, (16, 16), interpolation=cv2.INTER_AREA)
    normalized = cv2.equalizeHist(resized)
    return TEMPLATE_PREFIX + normalized.tobytes()


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_nist_meta(
    image_bytes: bytes, *, modality: str, position: str
) -> dict[str, Any]:
    """NIST-ITL-flavored capture metadata stored on the record."""
    with Image.open(io.BytesIO(image_bytes)) as img:
        width, height = img.size
        fmt = img.format or ""
        dpi = img.info.get("dpi")
    return {
        "std": "ANSI/NIST-ITL 1-2007 (subset)",
        "modality": modality,
        "position": position,
        "width": width,
        "height": height,
        "format": fmt,
        "dpi": list(dpi) if dpi else None,
        "sha256": sha256_hex(image_bytes),
    }

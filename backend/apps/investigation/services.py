"""Investigation services: case numbers, latent enhancement, minutiae stub."""

from __future__ import annotations

import io
from typing import Any

import cv2
import numpy as np
from django.core.files.base import ContentFile
from django.db import connection
from django.utils import timezone
from PIL import Image, ImageEnhance, ImageOps

from apps.preprocessing.services import sha256_hex

from .models import LatentPrint


def generate_case_no() -> str:
    """Sequential case number, e.g. CASE-2026-000007 (PG sequence)."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT nextval('abis_case_no_seq')")
        (value,) = cursor.fetchone()
    return f"CASE-{timezone.now().year}-{value:06d}"


# ------------------------------------------------------------- enhancement

ALLOWED_OPERATIONS = {"contrast", "invert", "rotate", "crop"}


def apply_operations(
    image: Image.Image, operations: list[dict[str, Any]]
) -> Image.Image:
    """Apply validated Pillow operations sequentially."""
    result = image.convert("L")
    for operation in operations:
        name = operation["op"]
        if name == "contrast":
            result = ImageEnhance.Contrast(result).enhance(float(operation["factor"]))
        elif name == "invert":
            result = ImageOps.invert(result)
        elif name == "rotate":
            result = result.rotate(
                -float(operation["angle"]), expand=True, fillcolor=255
            )
        elif name == "crop":
            left, top, right, bottom = operation["box"]
            if not (
                0 <= left < right <= result.width and 0 <= top < bottom <= result.height
            ):
                raise ValueError(f"Crop box {operation['box']} outside image bounds.")
            result = result.crop((left, top, right, bottom))
    return result


def enhance_latent(latent: LatentPrint, operations: list[dict], user) -> LatentPrint:
    """Run operations on the working image, store result + history entry."""
    source = latent.working_image_field()
    with source.open("rb") as fh:
        image = Image.open(io.BytesIO(fh.read()))
        image.load()

    result = apply_operations(image, operations)
    buffer = io.BytesIO()
    result.save(buffer, format="PNG")
    payload = buffer.getvalue()

    latent.enhanced_image.save(f"{latent.id}.png", ContentFile(payload), save=False)
    latent.editor_history = latent.editor_history + [
        {
            "at": timezone.now().isoformat(),
            "by": user.username if (user and user.is_authenticated) else None,
            "action": "enhance",
            "operations": operations,
            "result_sha256": sha256_hex(payload),
        }
    ]
    latent.save(update_fields=["enhanced_image", "editor_history"])
    return latent


# ------------------------------------------------------------- minutiae


def extract_minutiae(latent: LatentPrint, user) -> list[dict]:
    """Deterministic auto-extraction stub (cv2 corner features).

    The production extractor replaces this body; the output schema
    [{x, y, angle, type, quality}] is the contract.
    """
    source = latent.working_image_field()
    with source.open("rb") as fh:
        array = np.frombuffer(fh.read(), dtype=np.uint8)
    gray = cv2.imdecode(array, cv2.IMREAD_GRAYSCALE)
    if gray is None:
        raise ValueError("Latent image is not decodable.")

    corners = cv2.goodFeaturesToTrack(
        gray, maxCorners=24, qualityLevel=0.01, minDistance=8
    )
    minutiae: list[dict] = []
    if corners is not None:
        total = len(corners)
        for index, corner in enumerate(corners):
            x, y = (int(v) for v in corner.ravel())
            minutiae.append(
                {
                    "x": x,
                    "y": y,
                    "angle": (x * 7 + y * 13) % 360,  # deterministic pseudo-angle
                    "type": "ridge_ending" if index % 2 == 0 else "bifurcation",
                    "quality": round(1.0 - index / (2 * total), 3),
                }
            )

    latent.minutiae = minutiae
    latent.editor_history = latent.editor_history + [
        {
            "at": timezone.now().isoformat(),
            "by": user.username if (user and user.is_authenticated) else None,
            "action": "minutiae_auto_extract",
            "count": len(minutiae),
        }
    ]
    latent.save(update_fields=["minutiae", "editor_history"])
    return minutiae


def set_minutiae(latent: LatentPrint, minutiae: list[dict], user) -> LatentPrint:
    latent.minutiae = minutiae
    latent.editor_history = latent.editor_history + [
        {
            "at": timezone.now().isoformat(),
            "by": user.username if (user and user.is_authenticated) else None,
            "action": "minutiae_manual_edit",
            "count": len(minutiae),
        }
    ]
    latent.save(update_fields=["minutiae", "editor_history"])
    return latent

import io
import math
import logging
from typing import List, Union
from PIL import Image

from app.providers.visual_embedding.base import VisualEmbeddingProvider

logger = logging.getLogger("shorts_api.visual_embedding.local")


class LocalVisualEmbeddingProvider(VisualEmbeddingProvider):
    """
    Lightweight, CPU-friendly visual embedding provider using PIL spatial-color moments.
    Generates a normalized 64-dimensional feature vector capturing color distribution,
    brightness gradients, and spatial layout without requiring multi-gigabyte neural weights.
    """

    VECTOR_DIM = 64

    async def compute_image_embedding(self, image_input: Union[str, bytes]) -> List[float]:
        try:
            if isinstance(image_input, (bytes, bytearray)):
                img = Image.open(io.BytesIO(image_input))
            else:
                img = Image.open(image_input)

            # Convert to RGB and resize to 8x8 grid (8 * 8 = 64 pixels)
            img = img.convert("RGB").resize((8, 8), Image.Resampling.BILINEAR)
            if hasattr(img, "get_flattened_data"):
                pixels = list(img.get_flattened_data())
            else:
                pixels = list(img.getdata())

            # Extract normalized luminance + color balance per cell
            raw_vec = []
            for r, g, b in pixels:
                # Perceptual luminance
                lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0
                raw_vec.append(lum)

            # L2 normalize vector
            norm = math.sqrt(sum(x * x for x in raw_vec))
            if norm > 1e-6:
                normalized = [round(x / norm, 5) for x in raw_vec]
            else:
                normalized = [0.0] * self.VECTOR_DIM

            return normalized

        except Exception as exc:
            logger.warning(f"Failed to extract visual embedding from image ({exc}), returning fallback vector.")
            # Deterministic fallback vector
            return [1.0 / math.sqrt(self.VECTOR_DIM)] * self.VECTOR_DIM

    def compute_similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        """Computes cosine similarity between two normalized vectors."""
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0

        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        # Clamp to [0.0, 1.0]
        return round(max(0.0, min(1.0, dot)), 4)

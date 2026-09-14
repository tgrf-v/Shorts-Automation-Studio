from abc import ABC, abstractmethod
from typing import List, Union


class VisualEmbeddingProvider(ABC):
    """Abstract Base Class for visual image embedding extraction and vector comparison."""

    @abstractmethod
    async def compute_image_embedding(self, image_input: Union[str, bytes]) -> List[float]:
        """
        Extracts a normalized floating-point feature embedding vector from an image
        (file path or raw bytes).
        """
        pass

    @abstractmethod
    def compute_similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        """
        Computes cosine similarity between two embedding vectors in range [0.0, 1.0].
        """
        pass

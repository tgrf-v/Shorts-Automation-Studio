from app.providers.visual_embedding.base import VisualEmbeddingProvider
from app.providers.visual_embedding.local import LocalVisualEmbeddingProvider


def get_visual_embedding_provider() -> VisualEmbeddingProvider:
    """Returns singleton/instance of VisualEmbeddingProvider."""
    return LocalVisualEmbeddingProvider()


__all__ = [
    "VisualEmbeddingProvider",
    "LocalVisualEmbeddingProvider",
    "get_visual_embedding_provider",
]

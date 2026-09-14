import os
import sys
import io
import uuid
import unittest
import asyncio
from datetime import datetime, timezone

# Ensure app package is importable
_curr = os.path.dirname(os.path.abspath(__file__))
_root = os.path.abspath(os.path.join(_curr, ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from PIL import Image

from app.providers.footage_search import get_footage_search_provider
from app.providers.footage_search.base import RawCandidateItem, FootageSearchProvider
from app.providers.footage_search.mock import MockFootageSearchProvider
from app.providers.footage_search.youtube import YouTubeSearchProvider
from app.providers.footage_search.web import WebSearchProvider

from app.providers.visual_embedding import get_visual_embedding_provider
from app.providers.visual_embedding.base import VisualEmbeddingProvider
from app.providers.visual_embedding.local import LocalVisualEmbeddingProvider

from app.services.footage.query_generator import query_generator, FootageQueryGenerator
from app.services.footage.ranking_service import ranking_service, FootageRankingService
from app.schemas.footage import (
    FootageSearchRequest,
    FootageSearchResponse,
    FootageCandidateSchema,
    SceneFootageSelectionSchema,
    SceneFootageSummaryItem,
)


class TestFootageProviders(unittest.TestCase):
    """Unit tests for Footage Search Providers."""

    def test_provider_factory(self):
        self.assertIsInstance(get_footage_search_provider("mock"), MockFootageSearchProvider)
        self.assertIsInstance(get_footage_search_provider("youtube"), YouTubeSearchProvider)
        self.assertIsInstance(get_footage_search_provider("web"), WebSearchProvider)
        # Unknown provider safely falls back to MockFootageSearchProvider
        self.assertIsInstance(get_footage_search_provider("unknown_xyz"), MockFootageSearchProvider)

    def test_mock_footage_search_results(self):
        async def _run():
            provider = MockFootageSearchProvider()
            items = await provider.search("construction crane machinery", max_results=5)
            self.assertIsInstance(items, list)
            self.assertGreater(len(items), 0)
            self.assertLessEqual(len(items), 5)

            first = items[0]
            self.assertIsInstance(first, RawCandidateItem)
            self.assertTrue(first.title)
            self.assertTrue(first.url)
            self.assertTrue(first.thumbnail_url)
            self.assertIn(first.platform, ["youtube", "mock", "web"])
            self.assertGreater(first.duration, 0)

        asyncio.run(_run())

    def test_mock_footage_search_relevance(self):
        async def _run():
            provider = MockFootageSearchProvider()
            # Searching for crane should prioritize crane candidate
            crane_items = await provider.search("heavy industrial crane", max_results=3)
            self.assertTrue(any("crane" in item.title.lower() or "industrial" in item.title.lower() for item in crane_items))

        asyncio.run(_run())

    def test_youtube_provider_fallback_without_key(self):
        async def _run():
            # YouTube provider with no API key should cleanly fall back to mock
            provider = YouTubeSearchProvider(api_key="")
            items = await provider.search("aerial cityscape at night", max_results=4)
            self.assertIsInstance(items, list)
            self.assertGreater(len(items), 0)

        asyncio.run(_run())


class TestVisualEmbedding(unittest.TestCase):
    """Unit tests for Visual Embedding Provider."""

    def test_embedding_provider_factory(self):
        self.assertIsInstance(get_visual_embedding_provider(), LocalVisualEmbeddingProvider)

    def test_local_visual_embedding_generation(self):
        async def _run():
            provider = LocalVisualEmbeddingProvider()

            # Create a simple 64x64 synthetic image
            img = Image.new("RGB", (64, 64), color=(255, 100, 50))
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            img_bytes = buf.getvalue()

            vec = await provider.compute_image_embedding(img_bytes)
            self.assertEqual(len(vec), 64)
            # Verify normalized
            norm_sq = sum(v * v for v in vec)
            self.assertAlmostEqual(norm_sq, 1.0, places=2)

        asyncio.run(_run())

    def test_cosine_similarity(self):
        provider = LocalVisualEmbeddingProvider()

        # Identical vectors
        vec_a = [0.5, 0.5, 0.5, 0.5]
        sim_identical = provider.compute_similarity(vec_a, vec_a)
        self.assertAlmostEqual(sim_identical, 1.0, places=3)

        # Orthogonal vectors
        vec_b = [1.0, 0.0, 0.0]
        vec_c = [0.0, 1.0, 0.0]
        sim_ortho = provider.compute_similarity(vec_b, vec_c)
        self.assertAlmostEqual(sim_ortho, 0.0, places=3)

        # Empty vectors
        self.assertEqual(provider.compute_similarity([], []), 0.0)


class TestFootageQueryGenerator(unittest.TestCase):
    """Unit tests for Footage Query Generation."""

    def test_generate_queries_with_rich_inputs(self):
        queries = FootageQueryGenerator.generate_queries(
            description="A massive yellow excavator digging soil at sunset on a construction site",
            transcript_segment=[{"text": "Mesin raksasa ini mulai menggali pondasi gedung pencakar langit."}],
            max_queries=4,
        )

        self.assertIsInstance(queries, list)
        self.assertGreater(len(queries), 0)
        self.assertLessEqual(len(queries), 4)

        # Should contain descriptive English keywords extracted from visual description
        joined = " ".join(queries).lower()
        self.assertTrue("excavator" in joined or "construction" in joined or "sunset" in joined)

    def test_generate_queries_with_empty_inputs(self):
        queries = FootageQueryGenerator.generate_queries(
            description="",
            transcript_segment=None,
            max_queries=3,
        )
        self.assertGreaterEqual(len(queries), 1)
        self.assertTrue("cinematic" in queries[0].lower() or "footage" in queries[0].lower())


class TestFootageRankingService(unittest.TestCase):
    """Unit tests for Multi-Signal Footage Ranking."""

    def test_calculate_scores_formula(self):
        service = FootageRankingService()
        cand_vec = [1.0] + [0.0] * 63
        ref_vecs = [[1.0] + [0.0] * 63]

        ranking = service.compute_ranking(
            candidate_vector=cand_vec,
            reference_vectors=ref_vecs,
            title="Cinematic drone shot of construction excavator in 4k",
            description="High quality excavator digging on building site",
            scene_description="yellow excavator at construction site",
            duration=25.0,
            has_thumbnail=True,
            platform="youtube",
        )

        self.assertIn("visual_score", ranking)
        self.assertIn("context_score", ranking)
        self.assertIn("metadata_score", ranking)
        self.assertIn("final_score", ranking)
        self.assertIn("match_type", ranking)

        # High visual similarity test
        self.assertAlmostEqual(ranking["visual_score"], 1.0, places=2)
        self.assertGreaterEqual(ranking["final_score"], 0.70)
        self.assertIn(ranking["match_type"], ["Possible exact match", "High visual similarity"])

    def test_match_type_categorization(self):
        service = FootageRankingService()
        # Test low similarity
        cand_vec = [1.0] + [0.0] * 63
        ref_vecs = [[0.0, 1.0] + [0.0] * 62]  # Orthogonal

        ranking = service.compute_ranking(
            candidate_vector=cand_vec,
            reference_vectors=ref_vecs,
            title="Random nature forest waterfall",
            description="Nature footage",
            scene_description="Futuristic robotics laboratory",
            duration=300.0,
            has_thumbnail=False,
            platform="web",
        )

        self.assertIn(ranking["match_type"], ["Similar footage", "Contextually relevant"])


class TestFootageSchemas(unittest.TestCase):
    """Unit tests for Footage Pydantic schemas validation."""

    def test_footage_search_request_defaults(self):
        req = FootageSearchRequest()
        self.assertIsNone(req.provider)
        self.assertEqual(req.max_results, 20)
        self.assertIsNone(req.query)

    def test_footage_candidate_schema(self):
        now = datetime.now(timezone.utc)
        cand = FootageCandidateSchema(
            id=uuid.uuid4(),
            footage_search_id=uuid.uuid4(),
            scene_id=uuid.uuid4(),
            source_platform="youtube",
            source_url="https://youtube.com/watch?v=mock123",
            title="4K Heavy Machinery B-roll",
            description="Cinematic shot of heavy machinery",
            thumbnail_url="https://images.unsplash.com/photo-test",
            duration=14.5,
            context_score=0.75,
            visual_score=0.82,
            similarity_score=0.82,
            final_score=0.8145,
            match_type="Possible exact match",
            search_query="heavy machinery excavation",
            is_selected=True,
            created_at=now,
        )
        self.assertEqual(cand.title, "4K Heavy Machinery B-roll")
        self.assertTrue(cand.is_selected)
        self.assertEqual(cand.match_type, "Possible exact match")


if __name__ == "__main__":
    unittest.main()

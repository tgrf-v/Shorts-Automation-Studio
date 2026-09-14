import os
import re
import uuid
import logging
import httpx
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.scene import Scene
from app.models.keyframe import Keyframe
from app.models.footage_search import FootageSearch, FootageSearchStatus
from app.models.footage_candidate import FootageCandidate
from app.models.scene_footage_selection import SceneFootageSelection
from app.providers.storage.local import storage_provider
from app.providers.footage_search import get_footage_search_provider
from app.providers.visual_embedding import get_visual_embedding_provider
from app.services.footage.query_generator import query_generator
from app.services.footage.ranking_service import ranking_service
from app.services.footage.queue import footage_queue

logger = logging.getLogger("shorts_api.services.footage")


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_canonical_url(url: str) -> str:
    """Strips query trackers (utm, ref) for accurate URL deduplication."""
    clean = url.strip()
    clean = re.sub(r'([?&])(utm_[^&]+|ref=[^&]+|feature=[^&]+)', '', clean)
    clean = clean.rstrip('?&')
    return clean.lower()


class FootageService:
    """Orchestrates candidate search, visual embedding comparison, and scene footage selection."""

    def __init__(self):
        self.embedding_provider = get_visual_embedding_provider()

    @staticmethod
    async def create_and_enqueue_search(
        db: AsyncSession,
        scene_id: uuid.UUID,
        query: Optional[str] = None,
        provider: Optional[str] = None,
        max_results: int = 20
    ) -> FootageSearch:
        """
        Validates scene existence, generates queries if needed, creates a FootageSearch record,
        and pushes task to Redis queue.
        """
        # 1. Fetch scene
        stmt = select(Scene).where(Scene.id == scene_id)
        scene = (await db.execute(stmt)).scalar_one_or_none()
        if not scene:
            raise ValueError(f"Scene with ID '{scene_id}' not found.")

        # 2. Determine initial search query string
        if query and query.strip():
            final_query = query.strip()
        else:
            generated = query_generator.generate_queries(
                description=scene.description,
                transcript_segment=scene.transcript_segment,
                max_queries=1
            )
            final_query = generated[0] if generated else "viral short video"

        chosen_provider = (provider or getattr(settings, "FOOTAGE_SEARCH_PROVIDER", "youtube")).strip().lower()

        # 3. Create FootageSearch entity
        search_record = FootageSearch(
            project_id=scene.project_id,
            scene_id=scene.id,
            query=final_query,
            search_provider=chosen_provider,
            status=FootageSearchStatus.QUEUED,
            progress=0,
            current_step="Queued for search"
        )
        db.add(search_record)
        await db.commit()
        await db.refresh(search_record)

        # 4. Enqueue to Redis
        try:
            footage_queue.enqueue(
                search_id=str(search_record.id),
                scene_id=str(scene.id),
                project_id=str(scene.project_id)
            )
            logger.info(f"Enqueued footage search {search_record.id} for scene {scene.id}")
        except Exception as exc:
            logger.error(f"Failed to enqueue footage search: {exc}")
            search_record.status = FootageSearchStatus.FAILED
            search_record.error = f"Queue submission failed: {exc}"
            await db.commit()
            raise RuntimeError(f"Could not submit footage search task: {exc}") from exc

        return search_record

    @classmethod
    async def process_search_job(cls, search_id_str: str) -> None:
        """
        Background worker execution method. Executes query generation, queries search providers,
        deduplicates candidates, calculates visual and context scores, and saves ranked candidates.
        """
        logger.info(f"Processing footage search job: {search_id_str}")
        search_uuid = uuid.UUID(search_id_str)

        async with AsyncSessionLocal() as db:
            # 1. Fetch FootageSearch and Scene with Keyframes
            s_stmt = select(FootageSearch).where(FootageSearch.id == search_uuid)
            search = (await db.execute(s_stmt)).scalar_one_or_none()
            if not search:
                logger.error(f"FootageSearch '{search_id_str}' not found.")
                return

            sc_stmt = (
                select(Scene)
                .where(Scene.id == search.scene_id)
                .options(selectinload(Scene.keyframes))
            )
            scene = (await db.execute(sc_stmt)).scalar_one_or_none()
            if not scene:
                search.status = FootageSearchStatus.FAILED
                search.error = f"Scene '{search.scene_id}' not found."
                await db.commit()
                return

            # Update status to searching
            search.status = FootageSearchStatus.SEARCHING
            search.progress = 10
            search.current_step = "Generating discovery queries"
            await db.commit()

            try:
                # 2. Extract reference keyframe vectors
                ref_vectors: List[List[float]] = []
                emb_provider = get_visual_embedding_provider()

                for kf in scene.keyframes:
                    try:
                        full_img_path = storage_provider.get_full_path(kf.image_path)
                        if os.path.exists(full_img_path):
                            vec = await emb_provider.compute_image_embedding(full_img_path)
                            ref_vectors.append(vec)
                    except Exception as kf_exc:
                        logger.warning(f"Could not embed keyframe {kf.id}: {kf_exc}")

                logger.info(f"Loaded {len(ref_vectors)} reference keyframe embeddings for scene {scene.id}")

                # 3. Determine queries to execute
                queries_to_run = [search.query]
                # If search query was auto-generated, run multiple variations
                extra_queries = query_generator.generate_queries(
                    description=scene.description,
                    transcript_segment=scene.transcript_segment,
                    max_queries=getattr(settings, "FOOTAGE_MAX_QUERIES_PER_SCENE", 4)
                )
                for eq in extra_queries:
                    if eq.lower() not in [q.lower() for q in queries_to_run]:
                        queries_to_run.append(eq)

                # 4. Search Providers
                provider = get_footage_search_provider(search.search_provider)
                raw_candidates = []
                seen_urls = set()

                per_query_limit = getattr(settings, "FOOTAGE_MAX_RESULTS_PER_QUERY", 10)
                max_total = getattr(settings, "FOOTAGE_MAX_TOTAL_CANDIDATES", 30)

                search.progress = 25
                search.current_step = f"Querying {search.search_provider} ({len(queries_to_run)} variations)"
                await db.commit()

                for q in queries_to_run:
                    items = await provider.search(q, max_results=per_query_limit)
                    for item in items:
                        canon = normalize_canonical_url(item.url)
                        if canon not in seen_urls:
                            seen_urls.add(canon)
                            item.metadata["search_query"] = q
                            raw_candidates.append(item)
                            if len(raw_candidates) >= max_total:
                                break
                    if len(raw_candidates) >= max_total:
                        break

                logger.info(f"Collected {len(raw_candidates)} deduplicated candidates for search {search.id}")

                # 5. Visual Similarity & Ranking
                search.status = FootageSearchStatus.RANKING
                search.progress = 60
                search.current_step = "Computing visual similarity & ranking"
                await db.commit()

                ranked_entities: List[FootageCandidate] = []

                async with httpx.AsyncClient(timeout=8.0) as http_client:
                    for item in raw_candidates:
                        # Extract thumbnail embedding
                        cand_vec: List[float] = []
                        if item.thumbnail_url:
                            try:
                                # Fetch thumbnail bytes if HTTP
                                if item.thumbnail_url.startswith("http"):
                                    t_resp = await http_client.get(item.thumbnail_url)
                                    if t_resp.status_code == 200:
                                        cand_vec = await emb_provider.compute_image_embedding(t_resp.content)
                                elif os.path.exists(item.thumbnail_url):
                                    cand_vec = await emb_provider.compute_image_embedding(item.thumbnail_url)
                            except Exception as thumb_exc:
                                logger.debug(f"Thumbnail fetch failed ({thumb_exc}), using neutral score.")

                        # Calculate multi-signal scores
                        scores = ranking_service.compute_ranking(
                            candidate_vector=cand_vec,
                            reference_vectors=ref_vectors,
                            title=item.title,
                            description=item.description,
                            scene_description=scene.description,
                            duration=item.duration,
                            has_thumbnail=bool(item.thumbnail_url),
                            platform=item.platform
                        )

                        candidate_entity = FootageCandidate(
                            footage_search_id=search.id,
                            scene_id=scene.id,
                            source_platform=item.platform,
                            source_url=item.url,
                            video_url=item.video_url,
                            title=item.title,
                            description=item.description,
                            thumbnail_url=item.thumbnail_url,
                            creator=item.creator,
                            duration=item.duration,
                            published_at=item.published_at,
                            search_query=item.metadata.get("search_query", search.query),
                            context_score=scores["context_score"],
                            visual_score=scores["visual_score"],
                            similarity_score=scores["similarity_score"],
                            final_score=scores["final_score"],
                            match_type=scores["match_type"],
                            metadata_json=item.metadata
                        )
                        db.add(candidate_entity)
                        ranked_entities.append(candidate_entity)

                # 6. Finalize Search Entity
                search.status = FootageSearchStatus.COMPLETED
                search.progress = 100
                search.current_step = "Completed"
                search.total_results = len(ranked_entities)
                search.error = None

                await db.commit()
                logger.info(f"Footage search {search.id} completed. Stored {len(ranked_entities)} candidates.")

            except Exception as exc:
                logger.error(f"Footage search job {search.id} failed: {exc}", exc_info=True)
                search.status = FootageSearchStatus.FAILED
                search.error = str(exc)
                await db.commit()

    @staticmethod
    async def select_candidate(
        db: AsyncSession,
        candidate_id: uuid.UUID,
        notes: Optional[str] = None
    ) -> SceneFootageSelection:
        """Associates or updates the selected candidate footage for a scene."""
        c_stmt = select(FootageCandidate).where(FootageCandidate.id == candidate_id)
        candidate = (await db.execute(c_stmt)).scalar_one_or_none()
        if not candidate:
            raise ValueError(f"FootageCandidate '{candidate_id}' not found.")

        # Check existing selection for scene
        s_stmt = select(SceneFootageSelection).where(SceneFootageSelection.scene_id == candidate.scene_id)
        selection = (await db.execute(s_stmt)).scalar_one_or_none()

        if selection:
            selection.candidate_id = candidate.id
            selection.status = "selected"
            if notes is not None:
                selection.notes = notes
        else:
            selection = SceneFootageSelection(
                scene_id=candidate.scene_id,
                candidate_id=candidate.id,
                status="selected",
                notes=notes
            )
            db.add(selection)

        await db.commit()
        await db.refresh(selection)
        return selection

    @staticmethod
    async def get_scene_selection(
        db: AsyncSession,
        scene_id: uuid.UUID
    ) -> Optional[SceneFootageSelection]:
        """Returns the currently selected footage candidate for a scene."""
        stmt = (
            select(SceneFootageSelection)
            .where(SceneFootageSelection.scene_id == scene_id)
            .options(selectinload(SceneFootageSelection.candidate))
        )
        return (await db.execute(stmt)).scalar_one_or_none()


footage_service = FootageService()

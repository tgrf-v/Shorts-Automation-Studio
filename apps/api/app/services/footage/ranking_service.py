import re
import logging
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.providers.visual_embedding import get_visual_embedding_provider

logger = logging.getLogger("shorts_api.footage.ranking")


class FootageRankingService:
    """
    Multi-signal ranking engine combining visual similarity, context relevance,
    and metadata quality into a single unified candidate score.
    """

    def __init__(self):
        self.embedding_provider = get_visual_embedding_provider()

    def calculate_visual_score(
        self,
        candidate_vector: List[float],
        reference_vectors: List[List[float]]
    ) -> float:
        """
        Calculates aggregate visual similarity between candidate thumbnail and
        reference scene keyframe vectors using maximum pairwise similarity.
        """
        if not candidate_vector or not reference_vectors:
            # Neutral default if keyframes unavailable
            return 0.50

        sims = [
            self.embedding_provider.compute_similarity(candidate_vector, ref_vec)
            for ref_vec in reference_vectors
        ]
        max_sim = max(sims) if sims else 0.50
        return round(float(max_sim), 4)

    def calculate_context_score(
        self,
        title: str,
        description: Optional[str],
        scene_description: Optional[str],
        transcript_text: Optional[str] = None
    ) -> float:
        """
        Calculates textual relevance based on token overlap between candidate metadata
        and reference scene description / dialogue keywords.
        """
        cand_text = f"{title or ''} {description or ''}".lower()
        cand_tokens = set(re.findall(r'\b[a-zA-Z0-9]{3,}\b', cand_text))

        ref_text = f"{scene_description or ''} {transcript_text or ''}".lower()
        ref_tokens = set(re.findall(r'\b[a-zA-Z0-9]{3,}\b', ref_text))

        if not ref_tokens or not cand_tokens:
            return 0.40

        intersection = cand_tokens.intersection(ref_tokens)
        overlap = len(intersection) / float(len(ref_tokens))
        # Scale into reasonable score
        score = min(1.0, overlap * 2.5)
        return round(max(0.15, score), 4)

    def calculate_metadata_score(
        self,
        duration: Optional[float],
        has_thumbnail: bool,
        platform: str
    ) -> float:
        """
        Evaluates candidate technical quality (thumbnail presence, duration fit for Shorts).
        """
        score = 0.50

        # Thumbnail boost
        if has_thumbnail:
            score += 0.25

        # Short-form duration boost (10s to 60s is ideal for Shorts)
        if duration is not None:
            if 10.0 <= duration <= 75.0:
                score += 0.25
            elif 5.0 <= duration < 120.0:
                score += 0.15

        return min(1.0, round(score, 4))

    def compute_ranking(
        self,
        candidate_vector: List[float],
        reference_vectors: List[List[float]],
        title: str,
        description: Optional[str],
        scene_description: Optional[str],
        duration: Optional[float],
        has_thumbnail: bool,
        platform: str
    ) -> Dict[str, Any]:
        """
        Computes all component scores, weighted final score, and match type label.
        """
        w_visual = getattr(settings, "FOOTAGE_VISUAL_WEIGHT", 0.60)
        w_context = getattr(settings, "FOOTAGE_CONTEXT_WEIGHT", 0.25)
        w_meta = getattr(settings, "FOOTAGE_METADATA_WEIGHT", 0.15)

        visual_score = self.calculate_visual_score(candidate_vector, reference_vectors)
        context_score = self.calculate_context_score(title, description, scene_description)
        metadata_score = self.calculate_metadata_score(duration, has_thumbnail, platform)

        final_score = (visual_score * w_visual) + (context_score * w_context) + (metadata_score * w_meta)
        final_score = round(final_score, 4)

        # Match Type Labeling
        if visual_score >= 0.88 and final_score >= 0.85:
            match_type = "Possible exact match"
        elif visual_score >= 0.75 or final_score >= 0.75:
            match_type = "High visual similarity"
        elif final_score >= 0.55:
            match_type = "Similar footage"
        else:
            match_type = "Contextually relevant"

        return {
            "visual_score": visual_score,
            "context_score": context_score,
            "metadata_score": metadata_score,
            "final_score": final_score,
            "similarity_score": visual_score,
            "match_type": match_type
        }


ranking_service = FootageRankingService()

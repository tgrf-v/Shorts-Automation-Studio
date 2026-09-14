import re
import logging
from typing import List, Optional, Dict, Any

from app.core.config import settings

logger = logging.getLogger("shorts_api.footage.query_generator")

# Common stop words to exclude when extracting visual core keywords
STOP_WORDS = {
    "a", "an", "the", "in", "on", "at", "of", "and", "or", "to", "with",
    "is", "are", "was", "were", "this", "that", "scene", "video", "clip",
    "shows", "showing", "view", "footage", "looks", "appears", "background"
}


class FootageQueryGenerator:
    """
    Generates diverse, visually optimized search queries from reference scene context
    (visual description, keyframe elements, and narration transcript).
    """

    @classmethod
    def generate_queries(
        cls,
        description: Optional[str],
        transcript_segment: Optional[List[Dict[str, Any]]] = None,
        max_queries: Optional[int] = None
    ) -> List[str]:
        limit = max_queries or getattr(settings, "FOOTAGE_MAX_QUERIES_PER_SCENE", 4)
        desc = (description or "").strip()

        # Extract transcript words if available
        transcript_text = ""
        if transcript_segment:
            transcript_text = " ".join(
                seg.get("text", "") for seg in transcript_segment if isinstance(seg, dict)
            )

        queries: List[str] = []

        # 1. Exact-Context Query (from primary visual description)
        if desc:
            clean_desc = re.sub(r'[^a-zA-Z0-9\s]', ' ', desc)
            words = [w for w in clean_desc.split() if w.lower() not in STOP_WORDS]
            if words:
                queries.append(" ".join(words[:8]))

        # 2. Object-Action Query (focused on nouns & actions)
        if desc:
            clean_desc = re.sub(r'[^a-zA-Z0-9\s]', ' ', desc)
            words = [w for w in clean_desc.split() if len(w) > 3 and w.lower() not in STOP_WORDS]
            if len(words) >= 3:
                queries.append(f"{words[0]} {words[1]} {words[2]}")

        # 3. Transcript Keyword Query (narration hook)
        if transcript_text:
            clean_tr = re.sub(r'[^a-zA-Z0-9\s]', ' ', transcript_text)
            tr_words = [w for w in clean_tr.split() if len(w) > 3 and w.lower() not in STOP_WORDS]
            if tr_words:
                queries.append(" ".join(tr_words[:5]))

        # 4. Short Query (high-recall 3-4 word phrase)
        if desc:
            clean_desc = re.sub(r'[^a-zA-Z0-9\s]', ' ', desc)
            words = [w for w in clean_desc.split() if w.lower() not in STOP_WORDS]
            if len(words) >= 4:
                queries.append(f"{words[0]} {words[-1]} footage")

        # Fallback if queries empty
        if not queries:
            queries.append("short viral cinematic footage")

        # Deduplicate while preserving order
        seen = set()
        deduped = []
        for q in queries:
            normalized = q.strip().lower()
            if normalized and normalized not in seen:
                seen.add(normalized)
                deduped.append(q.strip())

        logger.info(f"Generated {len(deduped[:limit])} queries for scene: {deduped[:limit]}")
        return deduped[:limit]


query_generator = FootageQueryGenerator()

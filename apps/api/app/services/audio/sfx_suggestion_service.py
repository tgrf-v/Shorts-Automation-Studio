import re
import uuid
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.scene import Scene
from app.models.script import Script
from app.models.audio_segment import AudioSegment
from app.models.production_timeline import ProductionTimeline, ProductionTimelineItem
from app.models.caption import CaptionTrack, CaptionSegment

logger = logging.getLogger("shorts_api.services.audio.sfx_suggestion")


class SFXSuggestionItem(BaseModel):
    type: str = "sfx"
    category: str = Field(description="SFX sound category: impact, stinger, whoosh, discovery, success, click")
    keyword: str = Field(description="Matched trigger keyword from text or description")
    reason: str = Field(description="Human-readable explanation for why this SFX is suggested")
    recommended_position: float = Field(description="Recommended timestamp in seconds for SFX placement")
    recommended_volume: float = Field(default=-6.0, description="Recommended volume gain in dB")
    recommended_duration: float = Field(default=1.0, description="Estimated duration in seconds")


class SceneSFXSuggestionsResponse(BaseModel):
    scene_id: str
    scene_sequence: int
    suggestions: List[SFXSuggestionItem]


class SFXSuggestionService:
    """
    Rule-based SFX Suggestion engine for Indonesian Shorts narration and scenes.
    Analyzes scene visual descriptions, Indonesian narration script, and caption chunks.
    Suggestions are informational recommendations and are NEVER automatically applied.
    """

    # Keyword rules dictionary mapping category -> list of regex patterns and metadata
    RULES: Dict[str, Dict[str, Any]] = {
        "impact": {
            "keywords": [
                r"\bledakan\b", r"\bhancur\b", r"\bbom\b", r"\btabrakan\b",
                r"\bpecah\b", r"\bduar\b", r"\bbang\b", r"\bcrash\b", r"\bruntuh\b", r"\bhantam\b"
            ],
            "reason": "Impact/explosion keyword detected indicating dramatic physical action",
            "volume": -4.0,
            "duration": 1.2
        },
        "stinger": {
            "keywords": [
                r"\bmengejutkan\b", r"\bkaget\b", r"\btiba-tiba\b", r"\bwow\b",
                r"\bastaga\b", r"\bgila\b", r"\bshock\b", r"\bternyata\b", r"\btak disangka\b"
            ],
            "reason": "Dramatic suspense or surprise keyword detected indicating a revelation or stinger",
            "volume": -6.0,
            "duration": 1.0
        },
        "discovery": {
            "keywords": [
                r"\bmenemukan\b", r"\bmelihat\b", r"\bterbuka\b", r"\brahasia\b",
                r"\bterungkap\b", r"\bmisteri\b", r"\btahu\b", r"\bpenemuan\b", r"\baha\b"
            ],
            "reason": "Discovery or curiosity keyword detected indicating an inquisitive chime or whoosh",
            "volume": -6.0,
            "duration": 0.8
        },
        "whoosh": {
            "keywords": [
                r"\bcepat\b", r"\blari\b", r"\bmeluncur\b", r"\bterbang\b",
                r"\bgeser\b", r"\bkilat\b", r"\bluncur\b", r"\bkecepatan\b", r"\bzoom\b"
            ],
            "reason": "Fast motion or transition keyword detected indicating a swoosh/whoosh effect",
            "volume": -8.0,
            "duration": 0.6
        },
        "success": {
            "keywords": [
                r"\bsukses\b", r"\bmenang\b", r"\bberhasil\b", r"\bhebat\b",
                r"\bjuara\b", r"\bcuan\b", r"\blolos\b", r"\buntung\b"
            ],
            "reason": "Positive achievement or victory keyword detected indicating a success chime/tada",
            "volume": -6.0,
            "duration": 1.0
        },
        "click": {
            "keywords": [
                r"\bklik\b", r"\btekan\b", r"\bpilih\b", r"\btonton\b",
                r"\bsubscribe\b", r"\bingat\b", r"\bcatat\b", r"\blist\b"
            ],
            "reason": "Call-to-action or UI selection keyword detected indicating a pop/click effect",
            "volume": -6.0,
            "duration": 0.4
        }
    }

    @classmethod
    async def suggest_sfx_for_scene(
        cls,
        db: AsyncSession,
        scene_id: uuid.UUID
    ) -> SceneSFXSuggestionsResponse:
        """
        Analyzes a specific scene, its linked audio segment, script segment, and captions,
        and generates non-intrusive SFX placement suggestions.
        """
        scene_res = await db.execute(select(Scene).where(Scene.id == scene_id))
        scene = scene_res.scalar_one_or_none()
        if not scene:
            return SceneSFXSuggestionsResponse(
                scene_id=str(scene_id),
                scene_sequence=0,
                suggestions=[]
            )

        # Baseline timestamp: scene start time
        base_time = round(scene.start_time, 2)
        suggestions: List[SFXSuggestionItem] = []
        seen_categories = set()

        # 1. Inspect scene visual description
        desc_text = (scene.visual_description or "").lower()
        for cat, rule in cls.RULES.items():
            if cat in seen_categories:
                continue
            for pat in rule["keywords"]:
                match = re.search(pat, desc_text, re.IGNORECASE)
                if match:
                    kw = match.group(0)
                    suggestions.append(
                        SFXSuggestionItem(
                            category=cat,
                            keyword=kw,
                            reason=f"{rule['reason']} in visual description ('{kw}')",
                            recommended_position=base_time,
                            recommended_volume=rule["volume"],
                            recommended_duration=rule["duration"]
                        )
                    )
                    seen_categories.add(cat)
                    break

        # 2. Inspect active audio segment narration text
        audio_res = await db.execute(
            select(AudioSegment).where(AudioSegment.scene_id == scene_id)
        )
        audio_seg = audio_res.scalars().first()
        if audio_seg:
            narration_text = (audio_seg.text or "").lower()
            seg_start = round(audio_seg.start_time, 2)
            seg_duration = max(0.1, audio_seg.end_time - audio_seg.start_time)

            for cat, rule in cls.RULES.items():
                if cat in seen_categories:
                    continue
                for pat in rule["keywords"]:
                    match = re.search(pat, narration_text, re.IGNORECASE)
                    if match:
                        kw = match.group(0)
                        # Estimate keyword offset relative to segment length
                        char_pos = match.start()
                        total_len = max(1, len(narration_text))
                        time_offset = round((char_pos / total_len) * seg_duration, 2)
                        cue_time = round(seg_start + time_offset, 2)

                        suggestions.append(
                            SFXSuggestionItem(
                                category=cat,
                                keyword=kw,
                                reason=f"{rule['reason']} in narration text ('{kw}')",
                                recommended_position=cue_time,
                                recommended_volume=rule["volume"],
                                recommended_duration=rule["duration"]
                            )
                        )
                        seen_categories.add(cat)
                        break

        # If no keywords were found, offer a subtle transition whoosh at scene start
        if not suggestions:
            suggestions.append(
                SFXSuggestionItem(
                    category="whoosh",
                    keyword="scene_transition",
                    reason="Recommended subtle scene entry whoosh/transition",
                    recommended_position=base_time,
                    recommended_volume=-10.0,
                    recommended_duration=0.5
                )
            )

        return SceneSFXSuggestionsResponse(
            scene_id=str(scene.id),
            scene_sequence=scene.sequence,
            suggestions=suggestions
        )

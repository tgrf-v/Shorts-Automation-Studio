import os
import json
import base64
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import httpx
from pydantic import BaseModel, Field
from app.core.config import settings

logger = logging.getLogger("shorts_api.services.scene_description")


class SceneDescriptionResult(BaseModel):
    description: str = Field(..., description="Concise visual description of the scene")
    objects: List[str] = Field(default_factory=list, description="List of notable detected visual objects")
    actions: List[str] = Field(default_factory=list, description="Key actions occurring in the scene")
    environment: str = Field(default="indoor/studio", description="Environment or setting of the scene")


class VisionProvider(ABC):
    """Abstract Base Class defining the contract for visual scene description providers."""

    @abstractmethod
    async def describe_scene(
        self,
        keyframe_full_paths: List[str],
        transcript_context: str
    ) -> SceneDescriptionResult:
        """Analyzes keyframe images and transcript context to return structured scene description."""
        pass


class GeminiVisionProvider(VisionProvider):
    """Multimodal vision provider using Google Gemini API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.api_url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
        )

    async def describe_scene(
        self,
        keyframe_full_paths: List[str],
        transcript_context: str
    ) -> SceneDescriptionResult:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured.")

        # Prepare keyframe image parts
        parts: List[Dict[str, Any]] = []

        system_instruction = (
            "You are a professional video footage analyzer for short-form viral videos. "
            "Analyze the provided representative video keyframe images and spoken transcript context. "
            "Return a strictly valid JSON object with four keys: "
            "'description' (a concise 1-2 sentence description focusing on main subject, action, camera angle, and visual event. "
            "Avoid generic words like 'this video scene'; write specifically like 'A man in a red jacket sprinting across a foggy bridge.'), "
            "'objects' (an array of 3 to 6 key visual objects/props), "
            "'actions' (an array of 1 to 3 active verbs), and "
            "'environment' (a short phrase describing setting/lighting/location)."
        )

        parts.append({
            "text": f"System: {system_instruction}\nContext spoken in this scene: \"{transcript_context or 'No dialogue'}\""
        })

        # Attach up to 2 keyframes to keep payload lean and fast
        for path in keyframe_full_paths[:2]:
            if os.path.exists(path):
                try:
                    with open(path, "rb") as f:
                        b64_data = base64.b64encode(f.read()).decode("utf-8")
                    parts.append({
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": b64_data
                        }
                    })
                except Exception as exc:
                    logger.warning(f"Could not read keyframe {path} for Gemini: {exc}")

        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json"
            }
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(self.api_url, json=payload)
                response.raise_for_status()
                data = response.json()
                text_content = data["candidates"][0]["content"]["parts"][0]["text"]
                parsed = json.loads(text_content)

                return SceneDescriptionResult(
                    description=parsed.get("description", "A video scene capturing subject in action."),
                    objects=parsed.get("objects", []),
                    actions=parsed.get("actions", []),
                    environment=parsed.get("environment", "video setting")
                )
            except Exception as exc:
                logger.error(f"Gemini Vision API error: {exc}. Falling back to heuristic description.")
                return HeuristicVisionProvider().generate_from_context(transcript_context)


class HeuristicVisionProvider(VisionProvider):
    """Fallback provider generating structured descriptions from transcript context when no API key is provided."""

    @staticmethod
    def generate_from_context(transcript_context: str) -> SceneDescriptionResult:
        words = [w.strip(".,!?:;\"'") for w in transcript_context.lower().split() if len(w) > 3]
        sample_objects = list(dict.fromkeys(words[:4])) if words else ["subject", "focal element"]

        desc = (
            f"Scene showing visual sequence accompanied by narration: '{transcript_context[:100]}...'"
            if transcript_context
            else "Dynamic short-form video scene featuring key visual subject."
        )

        return SceneDescriptionResult(
            description=desc,
            objects=sample_objects or ["subject"],
            actions=["presenting", "demonstrating"],
            environment="studio / realistic scene"
        )

    async def describe_scene(
        self,
        keyframe_full_paths: List[str],
        transcript_context: str
    ) -> SceneDescriptionResult:
        return self.generate_from_context(transcript_context)


def get_vision_provider() -> VisionProvider:
    if settings.GEMINI_API_KEY and len(settings.GEMINI_API_KEY.strip()) > 10:
        return GeminiVisionProvider()
    return HeuristicVisionProvider()

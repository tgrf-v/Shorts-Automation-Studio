from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel, Field


class SceneContextItem(BaseModel):
    scene_id: str = Field(..., description="Unique scene identifier")
    sequence: int = Field(..., description="1-based sequence index")
    start_time: float = Field(..., description="Start timestamp in seconds")
    end_time: float = Field(..., description="End timestamp in seconds")
    duration: float = Field(..., description="Duration of this scene in seconds")
    visual_description: Optional[str] = Field(default=None, description="Visual description of scene elements")
    source_dialogue: Optional[str] = Field(default=None, description="Spoken dialogue in original reference")


class ScriptGenerationContext(BaseModel):
    project_name: str = Field(default="Shorts Video", description="Name of the project")
    source_language: str = Field(default="en", description="Source reference language")
    target_language: str = Field(default="id", description="Target output language")
    source_transcript_full: str = Field(..., description="Complete source transcript text")
    scenes: List[SceneContextItem] = Field(default_factory=list, description="List of detected scenes with timing and visuals")
    instructions: Optional[str] = Field(default=None, description="Optional custom user instructions")
    target_wpm: int = Field(default=150, description="Target narration speaking speed in words per minute")


class GeneratedSceneSegment(BaseModel):
    scene_id: str = Field(..., description="Matching scene identifier")
    sequence: int = Field(default=1, description="Scene sequence number")
    adapted_text: str = Field(..., description="Adapted Indonesian narration for this scene")


class GeneratedScriptPayload(BaseModel):
    title: str = Field(..., description="Catchy Indonesian title for YouTube Shorts")
    full_script: str = Field(..., description="Complete combined Indonesian narration script")
    segments: List[GeneratedSceneSegment] = Field(
        default_factory=list,
        description="Scene-aligned adapted narration segments"
    )


class ScriptGenerationProvider(ABC):
    """Abstract Base Class defining the contract for script adaptation LLM providers."""

    @abstractmethod
    async def generate_script(self, context: ScriptGenerationContext) -> GeneratedScriptPayload:
        """
        Generates an Indonesian Shorts script aligned with reference video scenes.
        """
        pass

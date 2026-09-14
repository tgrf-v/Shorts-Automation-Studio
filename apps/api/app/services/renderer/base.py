import uuid
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Callable
from pydantic import BaseModel, Field

from app.services.renderer.config import RenderConfig


class RenderClip(BaseModel):
    """Represents an individual video shot to be trimmed, scaled to 9:16, and sequenced."""
    scene_sequence: int
    scene_id: str
    footage_file_path: str
    timeline_start: float
    timeline_end: float
    duration: float
    trim_start: float = 0.0
    trim_end: float = 0.0
    transition: str = "cut"  # "cut" or "fade"


class AudioMixInput(BaseModel):
    """Multi-track audio inputs for final mixing."""
    narration_audio_path: Optional[str] = None
    narration_duration: float = 0.0
    bgm_inputs: List[Dict[str, Any]] = Field(default_factory=list)
    sfx_inputs: List[Dict[str, Any]] = Field(default_factory=list)
    ducking_enabled: bool = True
    ducking_level: float = -6.0


class RenderExecutionPlan(BaseModel):
    """Complete, self-contained specification for a render job."""
    job_id: str
    project_id: str
    workspace_dir: str
    output_video_path: str
    subtitle_path: Optional[str] = None
    clips: List[RenderClip]
    audio_mix: AudioMixInput
    config: RenderConfig
    total_duration: float


class RenderResult(BaseModel):
    """Outcome of a render job."""
    success: bool
    output_path: str
    duration: float = 0.0
    file_size: int = 0
    width: int = 1080
    height: int = 1920
    error: Optional[str] = None
    command_log: Optional[str] = None


class VideoRenderer(ABC):
    """Abstract interface for video composition and rendering engines."""

    @abstractmethod
    def build_ffmpeg_command(self, plan: RenderExecutionPlan) -> List[str]:
        """Constructs the deterministic FFmpeg CLI command list for the plan."""
        pass

    @abstractmethod
    async def render(
        self,
        plan: RenderExecutionPlan,
        progress_cb: Optional[Callable[[int, str], None]] = None
    ) -> RenderResult:
        """Executes the render execution plan and returns the outcome."""
        pass

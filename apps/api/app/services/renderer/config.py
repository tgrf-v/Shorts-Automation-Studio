import os
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class RenderConfig(BaseModel):
    """
    Configuration parameters for rendering vertical 9:16 YouTube Shorts video.
    Defaults to CPU-based libx264/aac with optimal 1080x1920 resolution.
    """
    width: int = Field(default=1080, description="Video width in pixels (9:16 standard)")
    height: int = Field(default=1920, description="Video height in pixels (9:16 standard)")
    fps: int = Field(default=30, description="Output frame rate (30 or 60)")
    video_codec: str = Field(default="libx264", description="FFmpeg video encoder")
    audio_codec: str = Field(default="aac", description="FFmpeg audio encoder")
    audio_bitrate: str = Field(default="192k", description="Audio bitrate")
    crf: int = Field(default=23, description="Constant Rate Factor quality (lower is better, 18-28)")
    preset: str = Field(default="medium", description="x264 preset (ultrafast to veryslow)")
    pixel_format: str = Field(default="yuv420p", description="Pixel color format for universal compatibility")
    container: str = Field(default="mp4", description="Output container format")

    # Path overrides
    ffmpeg_path: Optional[str] = Field(
        default_factory=lambda: os.getenv("FFMPEG_PATH", "ffmpeg"),
        description="Path to ffmpeg executable"
    )
    ffprobe_path: Optional[str] = Field(
        default_factory=lambda: os.getenv("FFPROBE_PATH", "ffprobe"),
        description="Path to ffprobe executable"
    )
    hardware_accel: Optional[str] = Field(
        default=None,
        description="Optional hardware acceleration (e.g. nvenc, amf, vaapi, videotoolbox)"
    )

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()

import os
import json
import asyncio
import logging
import subprocess
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("shorts_api.services.media_metadata")


class ExtractedMetadata(BaseModel):
    duration: Optional[float] = Field(default=None, description="Duration in seconds")
    width: Optional[int] = Field(default=None, description="Width in pixels")
    height: Optional[int] = Field(default=None, description="Height in pixels")
    fps: Optional[float] = Field(default=None, description="Frames per second")
    codec: Optional[str] = Field(default=None, description="Video codec name")
    size: int = Field(default=0, description="File size in bytes")
    container: Optional[str] = Field(default=None, description="Format container name")
    raw_info: Dict[str, Any] = Field(default_factory=dict, description="Raw ffprobe output or fallback info")


class MediaMetadataService:
    """Service to safely inspect media files using FFprobe with defensive fallbacks."""

    @staticmethod
    async def extract(file_path: str) -> ExtractedMetadata:
        """
        Extracts video technical metadata via FFprobe.
        Falls back defensively if FFprobe binary is unavailable or returns an error.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Media file not found at: {file_path}")

        file_size = os.path.getsize(file_path)

        loop = asyncio.get_running_loop()

        def _run_ffprobe() -> ExtractedMetadata:
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                file_path
            ]
            try:
                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=True,
                    timeout=15
                )
                data = json.loads(result.stdout)
                streams = data.get("streams", [])
                format_info = data.get("format", {})

                # Find first video stream
                video_stream = next(
                    (s for s in streams if s.get("codec_type") == "video"),
                    None
                )

                duration = None
                if "duration" in format_info:
                    try:
                        duration = round(float(format_info["duration"]), 2)
                    except (ValueError, TypeError):
                        duration = None

                width = None
                height = None
                fps = None
                codec = None

                if video_stream:
                    width = video_stream.get("width")
                    height = video_stream.get("height")
                    codec = video_stream.get("codec_name")

                    # Calculate FPS from avg_frame_rate (e.g. "30/1" or "30000/1001")
                    r_frame_rate = video_stream.get("avg_frame_rate") or video_stream.get("r_frame_rate")
                    if r_frame_rate and "/" in r_frame_rate:
                        num, den = r_frame_rate.split("/")
                        try:
                            if float(den) > 0:
                                fps = round(float(num) / float(den), 2)
                        except (ValueError, ZeroDivisionError):
                            fps = None

                return ExtractedMetadata(
                    duration=duration,
                    width=width,
                    height=height,
                    fps=fps,
                    codec=codec,
                    size=file_size,
                    container=format_info.get("format_name"),
                    raw_info={"streams_count": len(streams), "format": format_info.get("format_name")}
                )

            except (subprocess.SubprocessError, FileNotFoundError) as exc:
                logger.warning(
                    f"FFprobe extraction unavailable ({exc}). Using filesystem inspection fallback for {file_path}."
                )
                # Defensive fallback: return file size and placeholder metadata
                return ExtractedMetadata(
                    duration=None,
                    width=None,
                    height=None,
                    fps=None,
                    codec=None,
                    size=file_size,
                    container=os.path.splitext(file_path)[1].lstrip("."),
                    raw_info={"fallback": True, "reason": str(exc)}
                )

        return await loop.run_in_executor(None, _run_ffprobe)


media_metadata_service = MediaMetadataService()

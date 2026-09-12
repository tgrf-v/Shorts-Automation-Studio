import os
import re
import asyncio
import logging
import subprocess
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from app.services.analysis.transcription import TranscriptSegment

logger = logging.getLogger("shorts_api.services.scene_detection")


class DetectedScene(BaseModel):
    sequence: int = Field(..., description="1-based sequence index")
    start_time: float = Field(..., description="Start time in seconds")
    end_time: float = Field(..., description="End time in seconds")
    duration: float = Field(..., description="Duration in seconds")
    transcript_segments: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Aligned transcript segments overlapping this scene"
    )


class SceneDetectionService:
    """Service to detect visual scene changes and align them with transcript segments."""

    @staticmethod
    async def detect_scenes(
        video_path: str,
        total_duration: float,
        threshold: float = 0.3
    ) -> List[Dict[str, float]]:
        """
        Uses FFmpeg visual scene filter to find timestamps where visual cuts occur.
        Returns sorted list of cut boundaries [0.0, cut1, cut2, ..., total_duration].
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found at: {video_path}")

        loop = asyncio.get_running_loop()

        def _run_ffmpeg_scene_filter() -> List[float]:
            # FFmpeg select filter detects sudden frame difference score above threshold (0.0 - 1.0)
            cmd = [
                "ffmpeg",
                "-i", video_path,
                "-filter:v", f"select='gt(scene,{threshold})',showinfo",
                "-f", "null",
                "-"
            ]
            try:
                res = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=180
                )
                output = res.stderr

                # Extract timestamps from showinfo lines: e.g. "pts_time:3.456"
                pts_matches = re.findall(r"pts_time:([0-9]+\.?[0-9]*)", output)
                cuts = []
                for m in pts_matches:
                    try:
                        val = round(float(m), 3)
                        if 0.5 < val < (total_duration - 0.5):
                            # Avoid duplicate timestamps close together (< 0.8s)
                            if not cuts or (val - cuts[-1]) >= 0.8:
                                cuts.append(val)
                    except ValueError:
                        continue

                logger.info(f"FFmpeg detected {len(cuts)} scene transitions: {cuts}")
                return cuts
            except Exception as exc:
                logger.warning(f"FFmpeg scene detection error: {exc}. Proceeding with fallback.")
                return []

        cut_points = await loop.run_in_executor(None, _run_ffmpeg_scene_filter)

        # Build scene boundaries from cuts
        boundaries = [0.0] + sorted(cut_points) + [total_duration]

        # If video is long (> 8s) and no cut was detected, subdivide into reasonable intervals (4s - 6s)
        if len(cut_points) == 0 and total_duration > 8.0:
            step = 5.0
            boundaries = [0.0]
            current = step
            while current < total_duration:
                boundaries.append(round(current, 3))
                current += step
            boundaries.append(total_duration)

        scenes_raw = []
        for i in range(len(boundaries) - 1):
            s_start = round(boundaries[i], 3)
            s_end = round(boundaries[i + 1], 3)
            s_dur = round(s_end - s_start, 3)
            if s_dur >= 0.3:
                scenes_raw.append({
                    "start_time": s_start,
                    "end_time": s_end,
                    "duration": s_dur
                })

        return scenes_raw

    @staticmethod
    def align_transcript(
        scenes_raw: List[Dict[str, float]],
        segments: List[TranscriptSegment]
    ) -> List[DetectedScene]:
        """
        Aligns transcript segments to each scene.
        A transcript segment is associated with a scene if their time intervals overlap:
        max(scene.start, seg.start) < min(scene.end, seg.end)
        """
        aligned_scenes: List[DetectedScene] = []

        for idx, sc in enumerate(scenes_raw, start=1):
            s_start = sc["start_time"]
            s_end = sc["end_time"]
            s_dur = sc["duration"]

            overlapping = []
            for seg in segments:
                # Check for interval overlap
                overlap_start = max(s_start, seg.start)
                overlap_end = min(s_end, seg.end)
                if overlap_end > overlap_start:
                    overlapping.append({
                        "start": seg.start,
                        "end": seg.end,
                        "text": seg.text
                    })

            aligned_scenes.append(
                DetectedScene(
                    sequence=idx,
                    start_time=s_start,
                    end_time=s_end,
                    duration=s_dur,
                    transcript_segments=overlapping
                )
            )

        logger.info(f"Aligned {len(segments)} transcript segments across {len(aligned_scenes)} scenes.")
        return aligned_scenes


scene_detection_service = SceneDetectionService()

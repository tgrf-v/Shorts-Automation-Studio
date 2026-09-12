import os
import uuid
import asyncio
import logging
import tempfile
import subprocess
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from app.core.config import settings
from app.providers.storage.local import storage_provider

logger = logging.getLogger("shorts_api.services.keyframe_extraction")


class ExtractedKeyframe(BaseModel):
    timestamp: float = Field(..., description="Timestamp in seconds")
    image_path: str = Field(..., description="Relative storage path")
    quality_score: float = Field(default=0.0, description="Sharpness/variance quality score")


class KeyframeExtractionService:
    """Service to extract representative keyframes from scenes with sharpness quality scoring."""

    @staticmethod
    def _calculate_quality_score(image_path: str) -> float:
        """
        Calculates a sharpness score using Laplacian variance on grayscale image.
        Uses PIL ImageFilter.Kernel for high performance without requiring OpenCV.
        Higher score indicates sharper detail; lower score indicates blur/flat color.
        """
        try:
            from PIL import Image, ImageFilter, ImageStat
            with Image.open(image_path) as img:
                gray = img.convert("L")
                # Laplacian 3x3 filter kernel
                laplacian_kernel = [
                    0,  1, 0,
                    1, -4, 1,
                    0,  1, 0
                ]
                filtered = gray.filter(ImageFilter.Kernel((3, 3), laplacian_kernel, scale=1, offset=128))
                stat = ImageStat.Stat(filtered)
                variance = stat.var[0] if stat.var else 0.0
                return round(float(variance), 2)
        except Exception as exc:
            logger.warning(f"Could not compute sharpness score for {image_path}: {exc}")
            return 50.0  # Safe neutral fallback score

    @staticmethod
    async def extract_scene_keyframes(
        video_path: str,
        project_id: uuid.UUID,
        scene_id: uuid.UUID,
        start_time: float,
        duration: float,
        count: int = None
    ) -> List[ExtractedKeyframe]:
        """
        Extracts distributed keyframes across a scene interval and persists them.
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video not found: {video_path}")

        num_keyframes = count or settings.KEYFRAMES_PER_SCENE
        loop = asyncio.get_running_loop()

        # Compute distributed timestamps across the scene
        # e.g. for count=3: [20%, 50%, 80%] of duration
        timestamps: List[float] = []
        if num_keyframes == 1:
            timestamps.append(round(start_time + (duration * 0.5), 3))
        else:
            step = 1.0 / (num_keyframes + 1)
            for k in range(1, num_keyframes + 1):
                fraction = step * k
                ts = round(start_time + (duration * fraction), 3)
                timestamps.append(ts)

        extracted: List[ExtractedKeyframe] = []

        for idx, ts in enumerate(timestamps, start=1):
            temp_frame = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
            temp_frame_path = temp_frame.name
            temp_frame.close()

            def _extract_frame(target_ts: float, output_path: str):
                cmd = [
                    "ffmpeg",
                    "-y",
                    "-ss", str(target_ts),
                    "-i", video_path,
                    "-vframes", "1",
                    "-q:v", "2",
                    output_path
                ]
                subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=True,
                    timeout=30
                )

            try:
                await loop.run_in_executor(None, _extract_frame, ts, temp_frame_path)

                # Compute sharpness score
                score = KeyframeExtractionService._calculate_quality_score(temp_frame_path)

                # Read bytes and save to storage provider
                with open(temp_frame_path, "rb") as f:
                    content_bytes = f.read()

                filename = f"{scene_id}_{idx}.jpg"
                relative_path = await storage_provider.save(
                    project_id=str(project_id),
                    category="keyframes",
                    filename=filename,
                    content=content_bytes
                )

                extracted.append(
                    ExtractedKeyframe(
                        timestamp=ts,
                        image_path=relative_path,
                        quality_score=score
                    )
                )
            except Exception as exc:
                logger.error(f"Failed to extract keyframe at {ts}s: {exc}")
            finally:
                if os.path.exists(temp_frame_path):
                    try:
                        os.unlink(temp_frame_path)
                    except Exception:
                        pass

        logger.info(f"Extracted {len(extracted)} keyframes for scene {scene_id}")
        return extracted


keyframe_extraction_service = KeyframeExtractionService()

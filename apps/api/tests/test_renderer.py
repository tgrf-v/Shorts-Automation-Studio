import os
import sys
import uuid
import tempfile
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

# Ensure app package is importable
_curr = os.path.dirname(os.path.abspath(__file__))
_root = os.path.abspath(os.path.join(_curr, ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from app.models.render_job import RenderJob, RenderJobStatus
from app.models.caption import CaptionSegment
from app.services.renderer.config import RenderConfig
from app.services.renderer.subtitle_generator import SubtitleBurnInGenerator, format_ass_timestamp
from app.services.renderer.base import RenderExecutionPlan, RenderClip, AudioMixInput, RenderResult
from app.services.renderer.ffmpeg_renderer import FFmpegVideoRenderer, escape_ffmpeg_filter_path
from app.services.renderer.render_service import RenderService
from app.schemas.render import (
    RenderConfigSchema,
    RenderJobCreateRequest,
    RenderChecklistResponse,
    RenderJobSummary,
    RenderJobResponse
)


class TestRenderConfig(unittest.TestCase):
    """Unit tests for RenderConfig defaults and overrides."""

    def test_default_config_is_9_16_cpu_first(self):
        cfg = RenderConfig()
        self.assertEqual(cfg.width, 1080)
        self.assertEqual(cfg.height, 1920)
        self.assertEqual(cfg.fps, 30)
        self.assertEqual(cfg.video_codec, "libx264")
        self.assertEqual(cfg.audio_codec, "aac")
        self.assertEqual(cfg.crf, 23)
        self.assertEqual(cfg.preset, "medium")
        self.assertEqual(cfg.pixel_format, "yuv420p")
        self.assertEqual(cfg.container, "mp4")
        self.assertIsNone(cfg.hardware_accel)

    def test_config_overrides(self):
        cfg = RenderConfig(fps=60, crf=18, preset="fast")
        self.assertEqual(cfg.fps, 60)
        self.assertEqual(cfg.crf, 18)
        self.assertEqual(cfg.preset, "fast")


class TestSubtitleBurnInGenerator(unittest.TestCase):
    """Unit tests for ASS subtitle file generation."""

    def test_format_ass_timestamp(self):
        self.assertEqual(format_ass_timestamp(0.0), "0:00:00.00")
        self.assertEqual(format_ass_timestamp(1.25), "0:00:01.25")
        self.assertEqual(format_ass_timestamp(65.5), "0:01:05.50")
        self.assertEqual(format_ass_timestamp(3661.12), "1:01:01.12")

    def test_generate_ass_positions_and_styles(self):
        with tempfile.TemporaryDirectory() as td:
            out_file = os.path.join(td, "test_subs.ass")
            seg1 = MagicMock(spec=CaptionSegment)
            seg1.start_time = 0.0
            seg1.end_time = 2.5
            seg1.text = "Selamat datang di Shorts Studio!"
            seg1.style = "default"
            seg1.position = "bottom"

            seg2 = MagicMock(spec=CaptionSegment)
            seg2.start_time = 2.5
            seg2.end_time = 5.0
            seg2.text = "Perhatikan fakta mencengangkan ini."
            seg2.style = "highlight"
            seg2.position = "center"

            seg3 = MagicMock(spec=CaptionSegment)
            seg3.start_time = 5.0
            seg3.end_time = 8.0
            seg3.text = "Judul Teratas"
            seg3.style = "bold"
            seg3.position = "top"

            path = SubtitleBurnInGenerator.generate_ass([seg1, seg2, seg3], out_file)
            self.assertTrue(os.path.exists(path))

            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            # Verify header resolution
            self.assertIn("PlayResX: 1080", content)
            self.assertIn("PlayResY: 1920", content)

            # Verify styles
            self.assertIn("Style: Default", content)
            self.assertIn("Style: Bold", content)
            self.assertIn("Style: Highlight", content)

            # Verify alignment tags
            self.assertIn("{\\an2}Selamat datang", content)   # bottom
            self.assertIn("{\\an5}Perhatikan fakta", content) # center
            self.assertIn("{\\an8}Judul Teratas", content)   # top


class TestFFmpegCommandGeneration(unittest.TestCase):
    """Unit tests for FFmpeg CLI command construction & filter graph."""

    def setUp(self):
        self.renderer = FFmpegVideoRenderer()

    def test_escape_ffmpeg_path(self):
        p = r"C:\path\to\file:name.ass"
        escaped = escape_ffmpeg_filter_path(p)
        self.assertNotIn(r"\path", escaped)
        self.assertIn("/path/to/file", escaped)
        self.assertIn(r"C\:", escaped)

    def test_filter_complex_scale_crop_and_concat(self):
        cfg = RenderConfig()
        clips = [
            RenderClip(
                scene_sequence=1,
                scene_id=str(uuid.uuid4()),
                footage_file_path="scene1.mp4",
                timeline_start=0.0,
                timeline_end=3.5,
                duration=3.5,
                trim_start=1.0,
                trim_end=4.5
            ),
            RenderClip(
                scene_sequence=2,
                scene_id=str(uuid.uuid4()),
                footage_file_path="scene2.mp4",
                timeline_start=3.5,
                timeline_end=7.0,
                duration=3.5,
                trim_start=0.0,
                trim_end=3.5
            )
        ]
        audio_mix = AudioMixInput(
            narration_audio_path="narration.mp3",
            narration_duration=7.0,
            bgm_inputs=[{
                "file_path": "bgm.mp3",
                "volume_db": -18.0,
                "fade_in": 1.0,
                "fade_out": 2.0,
                "loop": True
            }],
            sfx_inputs=[{
                "file_path": "sfx.mp3",
                "volume_db": -6.0,
                "start_time": 3.5
            }]
        )

        plan = RenderExecutionPlan(
            job_id=str(uuid.uuid4()),
            project_id=str(uuid.uuid4()),
            workspace_dir="workspace",
            output_video_path="output.mp4",
            subtitle_path="subtitles.ass",
            clips=clips,
            audio_mix=audio_mix,
            config=cfg,
            total_duration=7.0
        )

        cmd = self.renderer.build_ffmpeg_command(plan)
        cmd_str = " ".join(cmd)

        # 1. Inputs verification
        self.assertIn("-ss 1.000 -t 3.500 -i scene1.mp4", cmd_str)
        self.assertIn("-t 3.500 -i scene2.mp4", cmd_str)

        # 2. 9:16 Scale and Center Crop verification
        self.assertIn("scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920:(in_w-1080)/2:(in_h-1920)/2", cmd_str)

        # 3. Concat verification
        self.assertIn("concat=n=2:v=1:a=0[vconcat]", cmd_str)

        # 4. Subtitle Burn-In
        self.assertIn("ass=", cmd_str)

        # 5. Output encoding parameters
        self.assertIn("-c:v libx264", cmd_str)
        self.assertIn("-crf 23", cmd_str)
        self.assertIn("-preset medium", cmd_str)
        self.assertIn("-pix_fmt yuv420p", cmd_str)
        self.assertIn("-c:a aac", cmd_str)
        self.assertIn("-b:a 192k", cmd_str)


class TestDependencyValidation(unittest.TestCase):
    """Unit tests for strict pre-flight dependency validation."""

    def test_missing_footage_scene_error_formatting(self):
        """Verify that a scene without footage causes an explicit failure message."""
        missing_scenes = [3, 5]
        scenes_str = ", ".join(f"Scene {seq}" for seq in missing_scenes)
        err = f"Cannot render project: {scenes_str} has no selected footage."
        self.assertIn("Scene 3", err)
        self.assertIn("Scene 5", err)
        self.assertIn("has no selected footage", err)


class TestRenderSchemas(unittest.TestCase):
    """Unit tests for Pydantic Render Schemas."""

    def test_render_checklist_schema(self):
        data = {
            "ready": False,
            "errors": ["Cannot render project: Scene 2 has no selected footage."],
            "warnings": ["No active caption track found."],
            "details": {"production_timeline": None}
        }
        res = RenderChecklistResponse(**data)
        self.assertFalse(res.ready)
        self.assertEqual(len(res.errors), 1)
        self.assertIn("Scene 2", res.errors[0])


if __name__ == "__main__":
    unittest.main()

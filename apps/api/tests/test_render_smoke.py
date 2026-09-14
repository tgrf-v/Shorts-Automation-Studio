import os
import sys
import uuid
import json
import shutil
import asyncio
import tempfile
import unittest
import subprocess
from datetime import datetime, timezone

# Ensure app package is importable
_curr = os.path.dirname(os.path.abspath(__file__))
_root = os.path.abspath(os.path.join(_curr, ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

try:
    import static_ffmpeg
    static_ffmpeg.add_paths()
except ImportError:
    pass

from app.services.renderer.config import RenderConfig
from app.services.renderer.base import RenderExecutionPlan, RenderClip, AudioMixInput, RenderResult
from app.services.renderer.ffmpeg_renderer import FFmpegVideoRenderer, escape_ffmpeg_filter_path
from app.services.renderer.subtitle_generator import SubtitleBurnInGenerator
from app.models.caption import CaptionSegment


class TestRenderSmoke(unittest.IsolatedAsyncioTestCase):
    """
    Milestone 11 Real Render Smoke Test.
    Uses native FFmpeg and FFprobe binaries to compose real vertical 1080x1920 MP4 video
    with multiple video clips, narration audio, and burned-in ASS captions.
    """

    @classmethod
    def setUpClass(cls):
        cls.ffmpeg_bin = shutil.which("ffmpeg")
        cls.ffprobe_bin = shutil.which("ffprobe")
        if not cls.ffmpeg_bin or not cls.ffprobe_bin:
            raise unittest.SkipTest("FFmpeg and FFprobe binaries not available on system PATH.")

    def setUp(self):
        # Force real rendering mode (disable mock output)
        self._prev_allow_mock = os.environ.get("ALLOW_MOCK_RENDER")
        self._prev_dry_run = os.environ.get("RENDERER_DRY_RUN")
        os.environ["ALLOW_MOCK_RENDER"] = "0"
        os.environ["RENDERER_DRY_RUN"] = "0"

        self.temp_dir = tempfile.TemporaryDirectory()
        self.td_path = self.temp_dir.name
        self.renderer = FFmpegVideoRenderer()

        # Generate test assets
        self.clip1_path = os.path.join(self.td_path, "clip1.mp4")
        self.clip2_path = os.path.join(self.td_path, "clip2.mp4")
        self.audio_path = os.path.join(self.td_path, "narration.wav")
        self.sub_path = os.path.join(self.td_path, "subtitles.ass")

        self._generate_synthetic_video(self.clip1_path, duration=1.5)
        self._generate_synthetic_video(self.clip2_path, duration=1.5)
        self._generate_synthetic_audio(self.audio_path, duration=3.0)
        self._generate_test_subtitles(self.sub_path)

    def tearDown(self):
        if self._prev_allow_mock is not None:
            os.environ["ALLOW_MOCK_RENDER"] = self._prev_allow_mock
        else:
            os.environ.pop("ALLOW_MOCK_RENDER", None)

        if self._prev_dry_run is not None:
            os.environ["RENDERER_DRY_RUN"] = self._prev_dry_run
        else:
            os.environ.pop("RENDERER_DRY_RUN", None)

        self.temp_dir.cleanup()

    def _generate_synthetic_video(self, output_path: str, duration: float = 1.5):
        """Generates a real 1080x1920 test video pattern using FFmpeg testsrc."""
        cmd = [
            self.ffmpeg_bin, "-y",
            "-f", "lavfi",
            "-i", f"testsrc=size=1080x1920:rate=30",
            "-t", str(duration),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            output_path
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"Failed to generate synthetic video: {res.stderr}")

    def _generate_synthetic_audio(self, output_path: str, duration: float = 3.0):
        """Generates a real sine wave audio file using FFmpeg."""
        cmd = [
            self.ffmpeg_bin, "-y",
            "-f", "lavfi",
            "-i", f"sine=frequency=440:duration={duration}",
            "-c:a", "pcm_s16le",
            "-ar", "44100",
            output_path
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"Failed to generate synthetic audio: {res.stderr}")

    def _generate_test_subtitles(self, output_path: str):
        """Generates a valid ASS subtitle track for the smoke test."""
        seg1 = CaptionSegment(
            sequence=1,
            start_time=0.0,
            end_time=1.5,
            text="Milestone 11 Smoke Test - Scene 1",
            style="default",
            position="bottom"
        )
        seg2 = CaptionSegment(
            sequence=2,
            start_time=1.5,
            end_time=3.0,
            text="Milestone 11 Smoke Test - Scene 2",
            style="highlight",
            position="bottom"
        )
        SubtitleBurnInGenerator.generate_ass([seg1, seg2], output_path)

    def _probe_video(self, video_path: str) -> dict:
        """Executes ffprobe to inspect container and stream metadata as JSON."""
        cmd = [
            self.ffprobe_bin,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            video_path
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"ffprobe failed: {res.stderr}")
        return json.loads(res.stdout)

    async def test_real_ffmpeg_smoke_render_with_subtitles_and_audio(self):
        """
        Synthesizes a complete 1080x1920 MP4 vertical video with 2 scenes,
        narration audio, and burned-in subtitles. Validates output streams using ffprobe.
        """
        output_path = os.path.join(self.td_path, "smoke_output.mp4")
        job_id = uuid.uuid4()
        proj_id = uuid.uuid4()

        clips = [
            RenderClip(
                scene_sequence=1,
                scene_id=str(uuid.uuid4()),
                footage_file_path=self.clip1_path,
                timeline_start=0.0,
                timeline_end=1.5,
                duration=1.5,
                trim_start=0.0,
                trim_end=1.5
            ),
            RenderClip(
                scene_sequence=2,
                scene_id=str(uuid.uuid4()),
                footage_file_path=self.clip2_path,
                timeline_start=1.5,
                timeline_end=3.0,
                duration=1.5,
                trim_start=0.0,
                trim_end=1.5
            )
        ]

        audio_mix = AudioMixInput(
            narration_audio_path=self.audio_path,
            narration_duration=3.0,
            bgm_inputs=[],
            sfx_inputs=[],
            ducking_enabled=False
        )

        cfg = RenderConfig(
            width=1080,
            height=1920,
            fps=30,
            video_codec="libx264",
            audio_codec="aac",
            preset="ultrafast",  # speed up smoke test
            crf=26
        )

        plan = RenderExecutionPlan(
            job_id=str(job_id),
            project_id=str(proj_id),
            workspace_dir=self.td_path,
            output_video_path=output_path,
            subtitle_path=self.sub_path,
            clips=clips,
            audio_mix=audio_mix,
            config=cfg,
            total_duration=3.0
        )

        progress_history = []
        def on_progress(pct: int, step: str):
            progress_history.append((pct, step))

        result = await self.renderer.render(plan, progress_cb=on_progress)

        self.assertTrue(result.success, f"Render failed: {result.error}")
        self.assertTrue(os.path.exists(output_path), "Render output file does not exist on disk.")
        self.assertGreater(os.path.getsize(output_path), 5000, "Rendered output file is suspiciously small.")
        self.assertGreater(len(progress_history), 0, "Progress callback was never invoked.")

        # Probe output with ffprobe
        probe_data = self._probe_video(output_path)
        format_info = probe_data.get("format", {})
        streams = probe_data.get("streams", [])

        # 1. Container check
        format_name = format_info.get("format_name", "")
        self.assertTrue(any(ext in format_name for ext in ["mp4", "mov"]), f"Unexpected container format: {format_name}")

        # 2. Duration check (3.0s ± 0.5s tolerance)
        duration = float(format_info.get("duration", 0.0))
        self.assertAlmostEqual(duration, 3.0, delta=0.5, msg=f"Unexpected video duration: {duration}s")

        # 3. Stream checks
        video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
        audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

        self.assertIsNotNone(video_stream, "No video stream found in rendered MP4.")
        self.assertIsNotNone(audio_stream, "No audio stream found in rendered MP4.")

        # 4. Video dimensions & codec
        self.assertEqual(video_stream.get("width"), 1080)
        self.assertEqual(video_stream.get("height"), 1920)
        self.assertEqual(video_stream.get("codec_name"), "h264")

        # 5. Audio codec & channels
        self.assertEqual(audio_stream.get("codec_name"), "aac")
        self.assertGreaterEqual(int(audio_stream.get("channels", 1)), 1)

    async def test_real_ffmpeg_smoke_render_without_subtitles(self):
        """Validates that rendering operates smoothly when subtitles are omitted."""
        output_path = os.path.join(self.td_path, "smoke_no_subs.mp4")
        job_id = uuid.uuid4()
        proj_id = uuid.uuid4()

        clips = [
            RenderClip(
                scene_sequence=1,
                scene_id=str(uuid.uuid4()),
                footage_file_path=self.clip1_path,
                timeline_start=0.0,
                timeline_end=1.5,
                duration=1.5,
                trim_start=0.0,
                trim_end=1.5
            )
        ]

        audio_mix = AudioMixInput(
            narration_audio_path=self.audio_path,
            narration_duration=1.5,
            bgm_inputs=[],
            sfx_inputs=[]
        )

        cfg = RenderConfig(
            width=1080,
            height=1920,
            fps=30,
            preset="ultrafast",
            crf=26
        )

        plan = RenderExecutionPlan(
            job_id=str(job_id),
            project_id=str(proj_id),
            workspace_dir=self.td_path,
            output_video_path=output_path,
            subtitle_path=None,
            clips=clips,
            audio_mix=audio_mix,
            config=cfg,
            total_duration=1.5
        )

        result = await self.renderer.render(plan)
        self.assertTrue(result.success, f"Render without subtitles failed: {result.error}")
        self.assertTrue(os.path.exists(output_path))

        probe_data = self._probe_video(output_path)
        video_stream = next((s for s in probe_data["streams"] if s.get("codec_type") == "video"), None)
        self.assertIsNotNone(video_stream)
        self.assertEqual(video_stream.get("width"), 1080)
        self.assertEqual(video_stream.get("height"), 1920)

    async def test_process_cancellation(self):
        """Validates that active FFmpeg process can be safely terminated via cancel_job."""
        job_id = uuid.uuid4()
        output_path = os.path.join(self.td_path, "cancelled_render.mp4")

        # Generate a longer 10s video clip so it stays active long enough to cancel
        long_clip = os.path.join(self.td_path, "long_clip.mp4")
        self._generate_synthetic_video(long_clip, duration=10.0)

        clips = [
            RenderClip(
                scene_sequence=1,
                scene_id=str(uuid.uuid4()),
                footage_file_path=long_clip,
                timeline_start=0.0,
                timeline_end=10.0,
                duration=10.0,
                trim_start=0.0,
                trim_end=10.0
            )
        ]
        audio_mix = AudioMixInput(
            narration_audio_path=self.audio_path,
            narration_duration=10.0,
            bgm_inputs=[],
            sfx_inputs=[]
        )
        cfg = RenderConfig(width=1080, height=1920, fps=30, preset="slow", crf=18)
        plan = RenderExecutionPlan(
            job_id=str(job_id),
            project_id=str(uuid.uuid4()),
            workspace_dir=self.td_path,
            output_video_path=output_path,
            subtitle_path=None,
            clips=clips,
            audio_mix=audio_mix,
            config=cfg,
            total_duration=10.0
        )

        render_task = asyncio.create_task(self.renderer.render(plan))
        await asyncio.sleep(0.3)  # Let subprocess spin up

        # Cancel the job
        cancelled = self.renderer.cancel_job(str(job_id))
        self.assertTrue(cancelled)

        result = await render_task
        self.assertFalse(result.success)
        self.assertIn("cancelled", result.error.lower())

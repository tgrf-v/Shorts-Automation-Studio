import os
import sys
import uuid
import wave
import struct
import unittest
import asyncio
import tempfile
from unittest.mock import patch, MagicMock

# Ensure app package is importable
_curr = os.path.dirname(os.path.abspath(__file__))
_root = os.path.abspath(os.path.join(_curr, ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from app.providers.tts import get_tts_provider
from app.providers.tts.base import TTSProvider, TTSAudioResult, TTSVoiceOption
from app.providers.tts.mock import MockTTSProvider
from app.providers.tts.google import GoogleTTSProvider
from app.providers.tts.elevenlabs import ElevenLabsProvider
from app.services.tts.audio_processor import audio_processor, AudioProcessorService
from app.schemas.tts import (
    TTSGenerateRequest,
    TTSGenerateResponse,
    AudioSegmentSchema,
    AudioTimelineSchema,
    TTSGenerationSummaryResponse,
    TTSGenerationResponse,
)


class TestTTSProviders(unittest.TestCase):
    """Unit tests for TTS Provider abstraction layer."""

    def test_provider_factory(self):
        self.assertIsInstance(get_tts_provider("mock"), MockTTSProvider)
        self.assertIsInstance(get_tts_provider("google"), GoogleTTSProvider)
        self.assertIsInstance(get_tts_provider("elevenlabs"), ElevenLabsProvider)
        # Unknown provider should fall back safely to MockTTSProvider
        self.assertIsInstance(get_tts_provider("unknown_provider_xyz"), MockTTSProvider)

    def test_mock_tts_provider_synthesis(self):
        async def _run():
            provider = MockTTSProvider()
            text = "Bayangkan sebuah mesin raksasa yang mampu memindahkan gunung dalam hitungan jam."
            res = await provider.synthesize(text=text, voice="mock-id-female")

            self.assertIsInstance(res, TTSAudioResult)
            self.assertEqual(res.audio_format, "wav")
            self.assertEqual(res.sample_rate, 44100)
            self.assertEqual(res.channels, 1)
            self.assertGreater(len(res.audio_bytes), 1000)
            self.assertGreater(res.duration, 2.0)

            # Verify the output bytes form a valid WAV file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(res.audio_bytes)
                tmp_path = tmp.name

            try:
                with wave.open(tmp_path, 'rb') as wf:
                    self.assertEqual(wf.getnchannels(), 1)
                    self.assertEqual(wf.getframerate(), 44100)
                    self.assertEqual(wf.getsampwidth(), 2)
                    frames = wf.getnframes()
                    self.assertGreater(frames, 0)
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

        asyncio.run(_run())

    def test_mock_tts_voices(self):
        async def _run():
            provider = MockTTSProvider()
            voices = await provider.get_available_voices()
            self.assertGreaterEqual(len(voices), 2)
            voice_ids = [v.id for v in voices]
            self.assertIn("mock-id-female", voice_ids)
            self.assertIn("mock-id-male", voice_ids)

        asyncio.run(_run())

    def test_google_tts_provider_voices(self):
        async def _run():
            provider = GoogleTTSProvider(api_key="test_key")
            voices = await provider.get_available_voices()
            self.assertGreaterEqual(len(voices), 4)
            voice_ids = [v.id for v in voices]
            self.assertIn("id-ID-Standard-A", voice_ids)
            self.assertIn("id-ID-Wavenet-A", voice_ids)

        asyncio.run(_run())

    def test_google_tts_missing_key_error(self):
        async def _run():
            provider = GoogleTTSProvider(api_key="")
            provider.api_key = ""  # Force empty
            with self.assertRaises(ValueError):
                await provider.synthesize("Halo dunia")

        asyncio.run(_run())

    def test_elevenlabs_provider_missing_key_error(self):
        async def _run():
            provider = ElevenLabsProvider(api_key="")
            provider.api_key = ""
            with self.assertRaises(ValueError):
                await provider.synthesize("Halo dunia")

        asyncio.run(_run())


class TestAudioProcessor(unittest.TestCase):
    """Tests for audio duration measurement and segment concatenation."""

    def _create_sample_wav(self, duration: float, sample_rate: int = 44100) -> str:
        """Helper to create a small valid WAV file for testing."""
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp_path = tmp.name
        tmp.close()

        num_samples = int(duration * sample_rate)
        with wave.open(tmp_path, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            raw = struct.pack(f'<{num_samples}h', *([1000] * num_samples))
            wf.writeframes(raw)

        return tmp_path

    def test_inspect_audio_wav(self):
        async def _run():
            wav_path = self._create_sample_wav(duration=2.5, sample_rate=44100)
            try:
                info = await audio_processor.inspect_audio(wav_path)
                self.assertAlmostEqual(info.duration, 2.5, places=1)
                self.assertEqual(info.sample_rate, 44100)
                self.assertEqual(info.channels, 1)
            finally:
                if os.path.exists(wav_path):
                    os.unlink(wav_path)

        asyncio.run(_run())

    def test_concatenate_segments_wav(self):
        async def _run():
            seg1 = self._create_sample_wav(duration=1.5, sample_rate=44100)
            seg2 = self._create_sample_wav(duration=2.0, sample_rate=44100)

            out_tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            out_path = out_tmp.name
            out_tmp.close()

            try:
                # Use pure python wave concatenation fallback test
                AudioProcessorService._concatenate_wav_fallback([seg1, seg2], out_path)
                info = await audio_processor.inspect_audio(out_path)
                self.assertAlmostEqual(info.duration, 3.5, places=1)
                self.assertEqual(info.channels, 1)
            finally:
                for p in (seg1, seg2, out_path):
                    if os.path.exists(p):
                        os.unlink(p)

        asyncio.run(_run())


class TestTTSSchemas(unittest.TestCase):
    """Tests for Pydantic request and response schemas."""

    def test_generate_request_defaults(self):
        req = TTSGenerateRequest()
        self.assertIsNone(req.script_id)
        self.assertIsNone(req.provider)
        self.assertIsNone(req.voice)

    def test_timeline_schema(self):
        gen_id = uuid.uuid4()
        proj_id = uuid.uuid4()
        script_id = uuid.uuid4()
        seg1_id = uuid.uuid4()
        seg2_id = uuid.uuid4()

        seg1 = AudioSegmentSchema(
            id=seg1_id,
            scene_id="scene_1",
            sequence=1,
            text="Kalimat pembuka narasi",
            start_time=0.0,
            end_time=3.25,
            duration=3.25,
            audio_path="projects/123/audio/seg_1.mp3"
        )
        seg2 = AudioSegmentSchema(
            id=seg2_id,
            scene_id="scene_2",
            sequence=2,
            text="Kalimat kedua fakta menarik",
            start_time=3.25,
            end_time=7.50,
            duration=4.25,
            audio_path="projects/123/audio/seg_2.mp3"
        )

        timeline = AudioTimelineSchema(
            generation_id=gen_id,
            project_id=proj_id,
            script_id=script_id,
            duration=7.50,
            segments_count=2,
            segments=[seg1, seg2]
        )

        self.assertEqual(timeline.duration, 7.50)
        self.assertEqual(len(timeline.segments), 2)
        self.assertEqual(timeline.segments[0].start_time, 0.0)
        self.assertEqual(timeline.segments[1].start_time, 3.25)


if __name__ == "__main__":
    unittest.main()

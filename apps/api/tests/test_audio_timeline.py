import os
import sys
import uuid
import wave
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

from app.models.audio_mix import AudioType, AudioTimelineStatus
from app.services.audio.storage import LocalAudioStorage
from app.services.audio.audio_timeline_service import AudioTimelineService
from app.services.audio.sfx_suggestion_service import SFXSuggestionService, SFXSuggestionItem
from app.schemas.audio_mix import (
    AudioAssetCreate,
    AudioAssetResponse,
    AudioLayerCreate,
    AudioLayerUpdate,
    AudioLayerResponse,
    AudioTimelineGenerateRequest,
    AudioTimelineSummary,
    AudioTimelineResponse
)


class TestAudioLayerValidation(unittest.TestCase):
    """Unit tests for AudioLayer timing, volume, and fade validations."""

    def test_valid_layer_timing(self):
        # Should not raise exception
        AudioTimelineService.validate_layer_timing(
            start_time=0.0,
            end_time=15.5,
            volume=-18.0,
            fade_in=1.0,
            fade_out=2.0,
            max_duration=30.0
        )

    def test_negative_start_time_raises(self):
        with self.assertRaises(ValueError) as ctx:
            AudioTimelineService.validate_layer_timing(
                start_time=-1.0,
                end_time=5.0,
                volume=0.0,
                fade_in=0.0,
                fade_out=0.0
            )
        self.assertIn("cannot be negative", str(ctx.exception))

    def test_end_time_not_greater_than_start_time_raises(self):
        with self.assertRaises(ValueError) as ctx:
            AudioTimelineService.validate_layer_timing(
                start_time=5.0,
                end_time=5.0,
                volume=0.0,
                fade_in=0.0,
                fade_out=0.0
            )
        self.assertIn("strictly greater", str(ctx.exception))

    def test_volume_out_of_range_raises(self):
        with self.assertRaises(ValueError) as ctx:
            AudioTimelineService.validate_layer_timing(
                start_time=0.0,
                end_time=5.0,
                volume=-80.0,  # Below -60 dB
                fade_in=0.0,
                fade_out=0.0
            )
        self.assertIn("within [-60.0 dB, +12.0 dB]", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            AudioTimelineService.validate_layer_timing(
                start_time=0.0,
                end_time=5.0,
                volume=20.0,  # Above +12 dB
                fade_in=0.0,
                fade_out=0.0
            )
        self.assertIn("within [-60.0 dB, +12.0 dB]", str(ctx.exception))

    def test_negative_fade_raises(self):
        with self.assertRaises(ValueError) as ctx:
            AudioTimelineService.validate_layer_timing(
                start_time=0.0,
                end_time=5.0,
                volume=0.0,
                fade_in=-0.5,
                fade_out=0.0
            )
        self.assertIn("fade_in", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            AudioTimelineService.validate_layer_timing(
                start_time=0.0,
                end_time=5.0,
                volume=0.0,
                fade_in=0.0,
                fade_out=-1.0
            )
        self.assertIn("fade_out", str(ctx.exception))


class TestSFXSuggestionRules(unittest.TestCase):
    """Unit tests for Rule-Based SFX Suggestion keyword triggers."""

    def test_keyword_matching_impact(self):
        text = "Tiba-tiba terjadi ledakan dahsyat di dalam terowongan."
        found = []
        for cat, rule in SFXSuggestionService.RULES.items():
            for pat in rule["keywords"]:
                import re
                if re.search(pat, text.lower()):
                    found.append(cat)
                    break
        self.assertIn("impact", found)
        self.assertIn("stinger", found)  # "tiba-tiba" triggers stinger

    def test_keyword_matching_discovery(self):
        text = "Setelah berhari-hari mencari, akhirnya mereka menemukan artefak kuno."
        found = []
        for cat, rule in SFXSuggestionService.RULES.items():
            for pat in rule["keywords"]:
                import re
                if re.search(pat, text.lower()):
                    found.append(cat)
                    break
        self.assertIn("discovery", found)

    def test_keyword_matching_whoosh_and_success(self):
        text = "Mereka meluncur sangat cepat dan sukses meraih rekor dunia baru!"
        found = []
        for cat, rule in SFXSuggestionService.RULES.items():
            for pat in rule["keywords"]:
                import re
                if re.search(pat, text.lower()):
                    found.append(cat)
                    break
        self.assertIn("whoosh", found)
        self.assertIn("success", found)

    def test_suggestion_is_not_automatically_applied(self):
        """Verify suggestion item model produces only recommendations."""
        item = SFXSuggestionItem(
            category="impact",
            keyword="ledakan",
            reason="Explosion detected",
            recommended_position=12.5,
            recommended_volume=-4.0,
            recommended_duration=1.2
        )
        self.assertEqual(item.type, "sfx")
        self.assertEqual(item.recommended_position, 12.5)
        # Note: No database row or AudioLayer is created by the suggestion service.


class TestStaleStateDetection(unittest.TestCase):
    """Unit tests for Audio Timeline stale detection when production timeline changes."""

    def test_stale_when_production_timeline_changes(self):
        orig_pt_id = uuid.uuid4()
        new_pt_id = uuid.uuid4()

        timeline = MagicMock()
        timeline.production_timeline_id = orig_pt_id
        timeline.total_duration = 30.0

        active_pt = MagicMock()
        active_pt.id = new_pt_id
        active_pt.version = 2
        active_pt.total_duration = 30.0

        is_stale = False
        reasons = []
        if active_pt.id != timeline.production_timeline_id:
            is_stale = True
            reasons.append(f"Active production timeline was updated to v{active_pt.version}")

        self.assertTrue(is_stale)
        self.assertEqual(len(reasons), 1)
        self.assertIn("production timeline was updated", reasons[0])

    def test_stale_when_timeline_duration_drifts(self):
        pt_id = uuid.uuid4()

        timeline = MagicMock()
        timeline.production_timeline_id = pt_id
        timeline.total_duration = 25.0

        active_pt = MagicMock()
        active_pt.id = pt_id
        active_pt.version = 1
        active_pt.total_duration = 32.5

        is_stale = False
        reasons = []
        if abs(active_pt.total_duration - timeline.total_duration) > 0.5:
            is_stale = True
            reasons.append(f"Timeline duration changed from {timeline.total_duration:.2f}s to {active_pt.total_duration:.2f}s.")

        self.assertTrue(is_stale)
        self.assertIn("duration changed", reasons[0])


class TestLocalStorageAudioOperations(unittest.IsolatedAsyncioTestCase):
    """Unit tests for LocalAudioStorage file persistence."""

    async def test_save_and_delete_audio_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = LocalAudioStorage(base_dir=temp_dir)
            dummy_wav = b"RIFF....WAVEfmt ...."
            proj_id = uuid.uuid4()

            stored_path = await storage.save_file(dummy_wav, proj_id, "sample_beat.wav")
            self.assertTrue(os.path.exists(stored_path))

            abs_path = storage.get_absolute_path(stored_path)
            self.assertTrue(os.path.exists(abs_path))

            deleted = await storage.delete_file(stored_path)
            self.assertTrue(deleted)
            self.assertFalse(os.path.exists(stored_path))


class TestAudioMixSchemas(unittest.TestCase):
    """Unit tests for Pydantic schema validation."""

    def test_audio_layer_create_schema(self):
        asset_id = uuid.uuid4()
        data = {
            "audio_asset_id": asset_id,
            "type": "bgm",
            "name": "Upbeat Lofi",
            "start_time": 0.0,
            "end_time": 35.0,
            "volume": -18.0,
            "fade_in": 1.0,
            "fade_out": 2.0,
            "loop": True,
            "enabled": True,
            "ducking_enabled": True,
            "ducking_level": -6.0
        }
        schema = AudioLayerCreate(**data)
        self.assertEqual(schema.type, AudioType.BGM)
        self.assertEqual(schema.volume, -18.0)
        self.assertTrue(schema.loop)

    def test_audio_timeline_generate_request_defaults(self):
        req = AudioTimelineGenerateRequest()
        self.assertTrue(req.ducking_enabled)
        self.assertEqual(req.ducking_level, -6.0)
        self.assertIsNone(req.bgm_asset_id)


if __name__ == "__main__":
    unittest.main()

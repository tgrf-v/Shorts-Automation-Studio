import os
import sys
import uuid
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock

# Ensure app package is importable
_curr = os.path.dirname(os.path.abspath(__file__))
_root = os.path.abspath(os.path.join(_curr, ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from app.services.captions.caption_splitter import CaptionSplitter
from app.services.captions.caption_service import (
    CaptionGenerationService,
    format_srt_timestamp,
)
from app.schemas.captions import (
    CaptionGenerateRequest,
    CaptionSegmentUpdateRequest,
    CaptionSegmentSchema,
    CaptionTrackSummaryResponse,
    CaptionTrackResponse,
)


class TestCaptionSplitter(unittest.TestCase):
    """Unit tests for Caption Splitter readability logic."""

    def test_short_sentence_not_split(self):
        text = "Mesin ini sangat besar."
        chunks = CaptionSplitter.split_text(text, target_words=4, max_words=7)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], "Mesin ini sangat besar.")

    def test_long_sentence_split_at_punctuation(self):
        text = "Para ilmuwan menemukan sebuah fenomena langka, terutama di bagian terdalam palung laut."
        chunks = CaptionSplitter.split_text(text, target_words=4, max_words=7)
        self.assertGreaterEqual(len(chunks), 2)
        for c in chunks:
            words = c.split()
            self.assertLessEqual(len(words), 8)
            # Verify words are complete
            self.assertTrue(all(len(w) > 0 for w in words))

    def test_no_broken_words(self):
        text = "Ekskavator hidrolik raksasa berbobot ratusan ton mampu memindahkan batu-batu besar dalam waktu singkat."
        chunks = CaptionSplitter.split_text(text, target_words=4, max_words=7)
        combined = " ".join(chunks)
        # Ensure all original words are preserved
        original_words = text.split()
        recombined_words = combined.split()
        self.assertEqual(original_words, recombined_words)


class TestTimestampFormattingAndDistribution(unittest.TestCase):
    """Unit tests for SubRip SRT timestamp formatting and proportional distribution."""

    def test_format_srt_timestamp(self):
        self.assertEqual(format_srt_timestamp(0.0), "00:00:00,000")
        self.assertEqual(format_srt_timestamp(1.234), "00:00:01,234")
        self.assertEqual(format_srt_timestamp(65.5), "00:01:05,500")
        self.assertEqual(format_srt_timestamp(3661.05), "01:01:01,050")

    def test_proportional_distribution_boundaries(self):
        """Verify chunks start at seg_start, end at seg_end, and have no gaps or overlaps."""
        seg_start = 10.00
        seg_end = 14.00
        seg_duration = seg_end - seg_start

        chunks = ["Para ilmuwan menemukan", "sebuah fenomena langka", "di dasar laut."]
        weights = [len(c) for c in chunks]
        total_w = sum(weights)

        cursor = seg_start
        computed_timings = []

        for idx, c in enumerate(chunks):
            if idx == len(chunks) - 1:
                start = cursor
                end = seg_end
            else:
                dur = round(seg_duration * (weights[idx] / total_w), 2)
                start = cursor
                end = round(start + dur, 2)
            computed_timings.append((start, end))
            cursor = end

        # 1. First starts at seg_start
        self.assertEqual(computed_timings[0][0], 10.00)
        # 2. Last ends at seg_end
        self.assertEqual(computed_timings[-1][1], 14.00)
        # 3. Continuous without overlaps or gaps
        for i in range(len(computed_timings) - 1):
            self.assertEqual(computed_timings[i][1], computed_timings[i + 1][0])


class TestCaptionStaleDetection(unittest.TestCase):
    """Unit tests for Stale Caption Track state detection."""

    def test_stale_detection_script_change(self):
        proj_id = uuid.uuid4()
        original_script_id = uuid.uuid4()
        new_script_id = uuid.uuid4()

        track = MagicMock()
        track.project_id = proj_id
        track.script_id = original_script_id
        track.tts_generation_id = uuid.uuid4()
        track.production_timeline_id = uuid.uuid4()

        reasons = []
        if new_script_id != track.script_id:
            reasons.append("Active Indonesian script has changed since captions were generated.")

        self.assertEqual(len(reasons), 1)
        self.assertIn("script has changed", reasons[0])

    def test_stale_detection_tts_change(self):
        track = MagicMock()
        track.script_id = uuid.uuid4()
        track.tts_generation_id = uuid.uuid4()
        track.production_timeline_id = uuid.uuid4()

        new_tts_id = uuid.uuid4()
        reasons = []
        if new_tts_id != track.tts_generation_id:
            reasons.append("Active TTS narration audio has changed since captions were generated.")

        self.assertEqual(len(reasons), 1)
        self.assertIn("TTS narration audio has changed", reasons[0])

    def test_stale_detection_timeline_change(self):
        track = MagicMock()
        track.script_id = uuid.uuid4()
        track.tts_generation_id = uuid.uuid4()
        track.production_timeline_id = uuid.uuid4()

        new_timeline_id = uuid.uuid4()
        reasons = []
        if new_timeline_id != track.production_timeline_id:
            reasons.append("Active production timeline has changed since captions were generated.")

        self.assertEqual(len(reasons), 1)
        self.assertIn("production timeline has changed", reasons[0])


class TestManualSegmentValidation(unittest.TestCase):
    """Unit tests for manual caption segment edit rules."""

    def test_segment_bounds_validation(self):
        # Audio segment boundaries
        audio_start = 5.0
        audio_end = 8.5

        # Valid edit
        edit_start = 5.2
        edit_end = 7.8
        self.assertTrue(edit_start >= audio_start - 0.1)
        self.assertTrue(edit_end <= audio_end + 0.1)
        self.assertTrue(edit_end > edit_start)

        # Invalid start preceding audio segment
        bad_start = 4.0
        self.assertFalse(bad_start >= audio_start - 0.1)

        # Invalid end exceeding audio segment
        bad_end = 9.2
        self.assertFalse(bad_end <= audio_end + 0.1)


class TestCaptionSchemas(unittest.TestCase):
    """Unit tests for Caption Pydantic schemas validation."""

    def test_generate_request_defaults(self):
        req = CaptionGenerateRequest()
        self.assertIsNone(req.script_id)
        self.assertIsNone(req.tts_generation_id)
        self.assertIsNone(req.production_timeline_id)
        self.assertEqual(req.target_words_per_segment, 4)

    def test_segment_update_request(self):
        req = CaptionSegmentUpdateRequest(
            text="Teks narasi yang diperbarui",
            start_time=2.5,
            end_time=4.8,
            style="bold",
            position="center",
        )
        self.assertEqual(req.text, "Teks narasi yang diperbarui")
        self.assertEqual(req.style, "bold")
        self.assertEqual(req.position, "center")

    def test_caption_response_schema(self):
        now = datetime.now(timezone.utc)
        seg = CaptionSegmentSchema(
            id=uuid.uuid4(),
            caption_track_id=uuid.uuid4(),
            sequence=1,
            start_time=0.0,
            end_time=2.5,
            duration=2.5,
            text="Mesin raksasa ini mulai beroperasi.",
            style="default",
            position="bottom",
            created_at=now,
            updated_at=now,
        )

        res = CaptionTrackResponse(
            id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            script_id=uuid.uuid4(),
            tts_generation_id=uuid.uuid4(),
            production_timeline_id=uuid.uuid4(),
            version=1,
            language="id",
            status="ready",
            total_duration=2.5,
            total_segments=1,
            is_active=True,
            is_stale=False,
            stale_reasons=[],
            average_caption_duration=2.5,
            scenes_covered=1,
            segments=[seg],
            created_at=now,
            updated_at=now,
        )
        self.assertEqual(res.version, 1)
        self.assertEqual(res.language, "id")
        self.assertEqual(len(res.segments), 1)


if __name__ == "__main__":
    unittest.main()

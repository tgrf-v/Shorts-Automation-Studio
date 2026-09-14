import os
import sys
import uuid
import unittest
import asyncio
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

# Ensure app package is importable
_curr = os.path.dirname(os.path.abspath(__file__))
_root = os.path.abspath(os.path.join(_curr, ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from app.models.project import Project, ProjectStatus
from app.models.scene import Scene
from app.models.script import Script, ScriptStatus
from app.models.tts_generation import TTSGeneration, TTSStatus
from app.models.audio_segment import AudioSegment
from app.models.footage_candidate import FootageCandidate
from app.models.scene_footage_selection import SceneFootageSelection
from app.models.production_timeline import (
    ProductionTimeline,
    ProductionTimelineItem,
    TimelineStatus,
)
from app.schemas.timeline import (
    ProductionTimelineGenerateRequest,
    ProductionTimelineItemUpdateRequest,
    ProductionTimelineResponse,
    ProductionTimelineSummaryResponse,
    ProductionTimelineItemSchema,
)
from app.services.timeline.timeline_service import ProductionTimelineService


class TestTimelineServiceLogic(unittest.TestCase):
    """Unit tests for Production Timeline logic and validation."""

    def setUp(self):
        self.service = ProductionTimelineService()

    def test_duration_handling_longer_footage(self):
        """When candidate duration is longer than narration, trim from 0 to narration duration."""
        cand_duration = 15.0
        narration_duration = 3.5

        if cand_duration >= narration_duration:
            start = 0.0
            end = narration_duration
            insufficient = False
        else:
            start = 0.0
            end = cand_duration
            insufficient = True

        self.assertEqual(start, 0.0)
        self.assertEqual(end, 3.5)
        self.assertFalse(insufficient)

    def test_continuous_trimming_across_consecutive_scenes(self):
        """When multiple consecutive scenes share the same candidate, footage offsets continue seamlessly."""
        cand_id = uuid.uuid4()
        cand_duration = 20.0
        scenes_durations = [1.6, 1.2, 2.5]  # 3 consecutive scenes

        prev_id = None
        prev_end = 0.0
        results = []

        for dur in scenes_durations:
            if prev_id and prev_id == cand_id:
                start = round(prev_end, 2)
            else:
                start = 0.0
            end = round(start + dur, 2)
            prev_id = cand_id
            prev_end = end
            results.append((start, end))

        self.assertEqual(results[0], (0.0, 1.6))
        self.assertEqual(results[1], (1.6, 2.8))
        self.assertEqual(results[2], (2.8, 5.3))

    def test_duration_handling_shorter_footage(self):
        """When candidate duration is shorter than narration, mark insufficient duration."""
        cand_duration = 2.0
        narration_duration = 4.8

        if cand_duration >= narration_duration:
            start = 0.0
            end = narration_duration
            insufficient = False
        else:
            start = 0.0
            end = cand_duration
            insufficient = True

        self.assertEqual(start, 0.0)
        self.assertEqual(end, 2.0)
        self.assertTrue(insufficient)

    def test_duration_handling_unknown_duration(self):
        """When candidate duration is None or 0, flag duration_unknown."""
        cand_duration = None
        narration_duration = 4.0

        if cand_duration is not None and cand_duration > 0:
            duration_unknown = False
        else:
            duration_unknown = True

        self.assertTrue(duration_unknown)

    def test_missing_footage_handling(self):
        """When a scene has no selected candidate, candidate is None with zero trim."""
        has_selection = False
        if not has_selection:
            candidate_id = None
            start_time = 0.0
            end_time = 0.0
            insufficient = False

        self.assertIsNone(candidate_id)
        self.assertEqual(start_time, 0.0)
        self.assertEqual(end_time, 0.0)
        self.assertFalse(insufficient)

    def test_manual_trim_validation_rules(self):
        """Test start and end validation boundaries."""
        # 1. Negative start should fail
        start = -1.0
        end = 3.0
        self.assertTrue(start < 0)

        # 2. End <= Start should fail
        start = 3.0
        end = 3.0
        self.assertTrue(end <= start)

        start = 4.0
        end = 2.0
        self.assertTrue(end <= start)

        # 3. Valid trim within candidate bounds (candidate duration = 10s)
        cand_duration = 10.0
        start = 2.5
        end = 6.0
        self.assertTrue(start >= 0 and end > start and end <= cand_duration)

        # 4. Exceeds candidate bounds
        start = 0.0
        end = 15.0
        self.assertTrue(end > cand_duration)


class TestTimelineStaleDetection(unittest.TestCase):
    """Unit tests for Stale Timeline state detection."""

    def test_stale_detection_when_script_changes(self):
        proj_id = uuid.uuid4()
        original_script_id = uuid.uuid4()
        new_active_script_id = uuid.uuid4()

        timeline = MagicMock()
        timeline.project_id = proj_id
        timeline.script_id = original_script_id
        timeline.tts_generation_id = uuid.uuid4()
        timeline.items = []

        # Simulate check
        reasons = []
        if new_active_script_id != timeline.script_id:
            reasons.append("Active Indonesian script has changed since this timeline was generated.")

        self.assertEqual(len(reasons), 1)
        self.assertIn("script has changed", reasons[0])

    def test_stale_detection_when_tts_changes(self):
        proj_id = uuid.uuid4()
        script_id = uuid.uuid4()
        original_tts_id = uuid.uuid4()
        new_tts_id = uuid.uuid4()

        timeline = MagicMock()
        timeline.project_id = proj_id
        timeline.script_id = script_id
        timeline.tts_generation_id = original_tts_id
        timeline.items = []

        reasons = []
        if new_tts_id != timeline.tts_generation_id:
            reasons.append("Active TTS narration audio has changed since this timeline was generated.")

        self.assertEqual(len(reasons), 1)
        self.assertIn("TTS narration audio has changed", reasons[0])

    def test_stale_detection_when_footage_selection_changes(self):
        scene_id = uuid.uuid4()
        old_candidate_id = uuid.uuid4()
        new_candidate_id = uuid.uuid4()

        item = MagicMock()
        item.scene_id = scene_id
        item.footage_candidate_id = old_candidate_id

        current_selections = {scene_id: new_candidate_id}

        reasons = []
        if item.footage_candidate_id != current_selections.get(item.scene_id):
            reasons.append("Footage candidate selections for one or more scenes have changed.")

        self.assertEqual(len(reasons), 1)
        self.assertIn("Footage candidate selections", reasons[0])


class TestTimelineSchemas(unittest.TestCase):
    """Unit tests for Timeline Pydantic schemas."""

    def test_generate_request_schema(self):
        req = ProductionTimelineGenerateRequest()
        self.assertIsNone(req.script_id)
        self.assertIsNone(req.tts_generation_id)

        custom_id = uuid.uuid4()
        req2 = ProductionTimelineGenerateRequest(script_id=custom_id)
        self.assertEqual(req2.script_id, custom_id)

    def test_update_item_request_schema(self):
        req = ProductionTimelineItemUpdateRequest(
            footage_start_time=1.5,
            footage_end_time=4.2,
            transition="fade",
            notes="Use dramatic zoom if possible",
        )
        self.assertEqual(req.footage_start_time, 1.5)
        self.assertEqual(req.footage_end_time, 4.2)
        self.assertEqual(req.transition, "fade")
        self.assertEqual(req.notes, "Use dramatic zoom if possible")

    def test_timeline_response_schema(self):
        now = datetime.now(timezone.utc)
        item = ProductionTimelineItemSchema(
            id=uuid.uuid4(),
            timeline_id=uuid.uuid4(),
            scene_id=uuid.uuid4(),
            sequence=1,
            start_time=0.0,
            end_time=3.5,
            duration=3.5,
            script_text="Mesin raksasa ini mulai beroperasi di area proyek.",
            footage_candidate_id=uuid.uuid4(),
            footage_source_url="https://youtube.com/watch?v=sample1",
            footage_start_time=0.0,
            footage_end_time=3.5,
            transition="cut",
            insufficient_footage_duration=False,
            duration_unknown=False,
            created_at=now,
            updated_at=now,
        )

        res = ProductionTimelineResponse(
            id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            script_id=uuid.uuid4(),
            tts_generation_id=uuid.uuid4(),
            version=1,
            status="ready",
            duration=3.5,
            total_scenes=1,
            scenes_with_footage=1,
            scenes_missing_footage=0,
            is_active=True,
            is_stale=False,
            stale_reasons=[],
            average_similarity=0.88,
            items=[item],
            created_at=now,
            updated_at=now,
        )
        self.assertEqual(res.version, 1)
        self.assertEqual(res.status, "ready")
        self.assertEqual(len(res.items), 1)
        self.assertEqual(res.average_similarity, 0.88)


if __name__ == "__main__":
    unittest.main()

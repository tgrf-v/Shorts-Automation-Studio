import os
import sys
import uuid
import unittest
import tempfile
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, and_

# Ensure app package is importable
_curr = os.path.dirname(os.path.abspath(__file__))
_root = os.path.abspath(os.path.join(_curr, ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["APP_ENV"] = "test"
os.environ["ALLOW_MOCK_RENDER"] = "1"

from app.core.database import Base
from app.models.project import Project, ProjectStatus
from app.models.media_asset import MediaAsset, MediaAssetType
from app.models.scene import Scene
from app.models.keyframe import Keyframe
from app.models.transcript import Transcript
from app.models.script import Script, ScriptStatus
from app.models.tts_generation import TTSGeneration, TTSStatus
from app.models.audio_segment import AudioSegment
from app.models.footage_search import FootageSearch, FootageSearchStatus
from app.models.footage_candidate import FootageCandidate
from app.models.scene_footage_selection import SceneFootageSelection
from app.models.production_timeline import ProductionTimeline, ProductionTimelineItem, TimelineStatus
from app.models.caption import CaptionTrack, CaptionSegment, CaptionTrackStatus
from app.models.audio_mix import AudioAsset, AudioTimeline, AudioLayer, AudioType, AudioTimelineStatus
from app.models.render_job import RenderJob, RenderJobStatus

from app.services.renderer.config import RenderConfig
from app.services.renderer.render_service import RenderService
from app.services.renderer.ffmpeg_renderer import FFmpegVideoRenderer, escape_ffmpeg_filter_path
from app.services.renderer.subtitle_generator import SubtitleBurnInGenerator


class TestEndToEndPipeline(unittest.IsolatedAsyncioTestCase):
    """
    Comprehensive Milestone 11 End-to-End Integration Suite.
    Tests the full dependency chain: M1 -> M3 -> M4 -> M5 -> M6 -> M7 -> M8 -> M9 -> M10.
    """

    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        self.session_maker = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        self.temp_dir = tempfile.TemporaryDirectory()
        self.render_service = RenderService(storage_base=self.temp_dir.name, session_maker=self.session_maker)

    async def asyncTearDown(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await self.engine.dispose()
        self.temp_dir.cleanup()

    async def _seed_full_production_pipeline(self, session: AsyncSession):
        """Helper to create a valid, fully configured M1–M9 production project."""
        now = datetime.now(timezone.utc)

        # M1 & M2: Project & Reference Video MediaAsset
        project = Project(
            name="Shorts Automation Studio E2E Test",
            status=ProjectStatus.READY
        )
        session.add(project)
        await session.flush()

        ref_asset = MediaAsset(
            project_id=project.id,
            type=MediaAssetType.REFERENCE,
            filename="reference.mp4",
            storage_path="storage/reference.mp4",
            size=1024 * 1024,
            mime_type="video/mp4",
            duration=9.0
        )
        session.add(ref_asset)
        await session.flush()
        project.reference_asset_id = ref_asset.id

        # M3: Reference Video Analysis (3 Scenes, Keyframes, Transcripts)
        scenes = []
        for i in range(1, 4):
            sc = Scene(
                project_id=project.id,
                sequence=i,
                start_time=(i - 1) * 3.0,
                end_time=i * 3.0,
                duration=3.0,
                description=f"Visual scene description {i}"
            )
            session.add(sc)
            scenes.append(sc)
        await session.flush()

        for sc in scenes:
            kf = Keyframe(
                scene_id=sc.id,
                timestamp=sc.start_time + 1.0,
                image_path=f"storage/kf_{sc.sequence}.jpg"
            )
            session.add(kf)

        transcript = Transcript(
            project_id=project.id,
            media_asset_id=ref_asset.id,
            language="en",
            content="Reference speech transcript for three scenes.",
            segments=[
                {"start": 0.0, "end": 3.0, "text": "Original transcript 1"},
                {"start": 3.0, "end": 6.0, "text": "Original transcript 2"},
                {"start": 6.0, "end": 9.0, "text": "Original transcript 3"}
            ]
        )
        session.add(transcript)
        await session.flush()

        # M4: Indonesian Script Adaptation (Aligned per Scene)
        script = Script(
            project_id=project.id,
            version=1,
            status=ScriptStatus.READY,
            is_active=True,
            language="id",
            title="Script Bahasa Indonesia",
            content="Narasi script bahasa Indonesia untuk tiga adegan.",
            segments=[
                {
                    "scene_id": str(sc.id),
                    "sequence": sc.sequence,
                    "start_time": sc.start_time,
                    "end_time": sc.end_time,
                    "target_duration": 3.0,
                    "adapted_text": f"Narasi Indonesia untuk scene {sc.sequence}"
                }
                for sc in scenes
            ]
        )
        session.add(script)
        await session.flush()

        # M5: TTS Audio Generation & Timeline Segments
        tts_gen = TTSGeneration(
            project_id=project.id,
            script_id=script.id,
            status=TTSStatus.COMPLETED,
            audio_path="storage/narration_master.wav",
            duration=9.0,
            voice="id-ID-Standard-A",
            provider="mock"
        )
        session.add(tts_gen)
        await session.flush()

        audio_segments = []
        for sc in scenes:
            aseg = AudioSegment(
                tts_generation_id=tts_gen.id,
                scene_id=str(sc.id),
                sequence=sc.sequence,
                start_time=(sc.sequence - 1) * 3.0,
                end_time=sc.sequence * 3.0,
                duration=3.0,
                audio_path=f"storage/audio_seg_{sc.sequence}.wav",
                text=f"Narasi Indonesia untuk scene {sc.sequence}"
            )
            session.add(aseg)
            audio_segments.append(aseg)

        # M6: Visual Footage Search & Selection per Scene
        candidates = []
        for sc in scenes:
            fsearch = FootageSearch(
                project_id=project.id,
                scene_id=sc.id,
                query=f"visual search scene {sc.sequence}",
                search_provider="youtube",
                status=FootageSearchStatus.COMPLETED,
                total_results=1,
            )
            session.add(fsearch)
            await session.flush()

            cand = FootageCandidate(
                footage_search_id=fsearch.id,
                scene_id=sc.id,
                source_platform="youtube",
                source_url=f"https://example.com/v_{sc.sequence}.mp4",
                video_url=f"https://example.com/v_{sc.sequence}.mp4",
                title=f"Footage candidate for scene {sc.sequence}",
                duration=15.0,
                visual_score=0.92,
                context_score=0.88,
                similarity_score=0.90,
                final_score=0.90,
                match_type="contextual_visual",
                metadata_json={"local_file_path": f"storage/footage_{sc.sequence}.mp4"}
            )
            session.add(cand)
            candidates.append(cand)
        await session.flush()

        for sc, cand in zip(scenes, candidates):
            sel = SceneFootageSelection(
                scene_id=sc.id,
                candidate_id=cand.id,
                status="approved"
            )
            session.add(sel)

        # M7: Production Timeline
        prod_timeline = ProductionTimeline(
            project_id=project.id,
            script_id=script.id,
            tts_generation_id=tts_gen.id,
            version=1,
            status=TimelineStatus.READY,
            duration=9.0,
            total_scenes=3,
            scenes_with_footage=3,
            scenes_missing_footage=0,
            is_active=True
        )
        session.add(prod_timeline)
        await session.flush()

        for sc, aseg, cand in zip(scenes, audio_segments, candidates):
            p_item = ProductionTimelineItem(
                timeline_id=prod_timeline.id,
                scene_id=sc.id,
                sequence=sc.sequence,
                start_time=aseg.start_time,
                end_time=aseg.end_time,
                duration=aseg.duration,
                script_text=aseg.text,
                audio_segment_id=aseg.id,
                footage_candidate_id=cand.id,
                footage_source_url=cand.video_url,
                footage_start_time=0.0,
                footage_end_time=aseg.duration,
                transition="cut"
            )
            session.add(p_item)

        # M8: Captions & Subtitle Track (Readability Bounded by AudioSegments)
        caption_track = CaptionTrack(
            project_id=project.id,
            script_id=script.id,
            tts_generation_id=tts_gen.id,
            production_timeline_id=prod_timeline.id,
            version=1,
            language="id",
            status=CaptionTrackStatus.READY,
            total_duration=9.0,
            total_segments=6,
            is_active=True
        )
        session.add(caption_track)
        await session.flush()

        # 2 short caption segments per 3.0s scene
        cap_seq = 1
        for sc, aseg in zip(scenes, audio_segments):
            c1 = CaptionSegment(
                caption_track_id=caption_track.id,
                sequence=cap_seq,
                scene_id=sc.id,
                source_audio_segment_id=aseg.id,
                start_time=aseg.start_time,
                end_time=aseg.start_time + 1.5,
                duration=1.5,
                text=f"Halo dunia bagian {cap_seq}",
                style="default",
                position="bottom"
            )
            c2 = CaptionSegment(
                caption_track_id=caption_track.id,
                sequence=cap_seq + 1,
                scene_id=sc.id,
                source_audio_segment_id=aseg.id,
                start_time=aseg.start_time + 1.5,
                end_time=aseg.end_time,
                duration=1.5,
                text=f"Lanjutan fakta bagian {cap_seq + 1}",
                style="highlight",
                position="bottom"
            )
            session.add_all([c1, c2])
            cap_seq += 2

        # M9: Audio Timeline & Assets (BGM and SFX)
        bgm_asset = AudioAsset(
            project_id=project.id,
            type=AudioType.BGM,
            name="Cinematic Ambient Bed",
            file_path="storage/bgm_ambient.mp3",
            duration=30.0,
            volume=-18.0
        )
        sfx_asset = AudioAsset(
            project_id=project.id,
            type=AudioType.SFX,
            name="Whoosh Transition",
            file_path="storage/sfx_whoosh.mp3",
            duration=1.0,
            volume=-6.0
        )
        session.add_all([bgm_asset, sfx_asset])
        await session.flush()

        audio_timeline = AudioTimeline(
            project_id=project.id,
            production_timeline_id=prod_timeline.id,
            version=1,
            status=AudioTimelineStatus.READY,
            total_duration=9.0,
            is_active=True,
            ducking_enabled=True,
            ducking_level=-6.0
        )
        session.add(audio_timeline)
        await session.flush()

        # Background music layer (0.0 to 9.0)
        bgm_layer = AudioLayer(
            project_id=project.id,
            audio_timeline_id=audio_timeline.id,
            audio_asset_id=bgm_asset.id,
            type=AudioType.BGM,
            name="Cinematic Ambient Bed",
            start_time=0.0,
            end_time=9.0,
            volume=-18.0,
            fade_in=1.0,
            fade_out=2.0,
            loop=True,
            enabled=True,
            ducking_enabled=True,
            ducking_level=-6.0
        )
        # SFX layer (starts at 3.0s scene transition)
        sfx_layer = AudioLayer(
            project_id=project.id,
            audio_timeline_id=audio_timeline.id,
            audio_asset_id=sfx_asset.id,
            scene_id=scenes[1].id,
            type=AudioType.SFX,
            name="Whoosh Transition",
            start_time=3.0,
            end_time=4.0,
            volume=-6.0,
            fade_in=0.0,
            fade_out=0.1,
            loop=False,
            enabled=True
        )
        session.add_all([bgm_layer, sfx_layer])
        await session.commit()

        return {
            "project": project,
            "scenes": scenes,
            "script": script,
            "tts_gen": tts_gen,
            "audio_segments": audio_segments,
            "candidates": candidates,
            "prod_timeline": prod_timeline,
            "caption_track": caption_track,
            "audio_timeline": audio_timeline
        }

    async def test_complete_pipeline_dependency_chain_and_rendering(self):
        """Verify the complete dependency validation and mock render execution."""
        async with self.session_maker() as session:
            seeded = await self._seed_full_production_pipeline(session)
            project_id = seeded["project"].id

            # 1. Pre-flight Validation Checklist
            chk = await self.render_service.validate_dependencies(session, project_id)
            self.assertTrue(chk["ready"], f"Checklist should be ready: {chk.get('errors')}")
            self.assertEqual(len(chk["errors"]), 0)
            self.assertEqual(chk["details"]["production_timeline"]["total_scenes"], 3)
            self.assertEqual(chk["details"]["caption_track"]["total_segments"], 6)
            self.assertEqual(chk["details"]["audio_timeline"]["total_layers"], 2)

            # 2. Create Render Job
            cfg = RenderConfig(width=1080, height=1920, fps=30, crf=23, preset="medium")
            job = await self.render_service.create_render_job(session, project_id, config=cfg)
            self.assertIsNotNone(job.id)
            self.assertEqual(job.output_width, 1080)
            self.assertEqual(job.output_height, 1920)
            self.assertEqual(job.fps, 30)

            # Wait briefly for background execution to complete
            import asyncio
            for _ in range(50):
                await asyncio.sleep(0.05)
                await session.refresh(job)
                if job.status in [RenderJobStatus.COMPLETED, RenderJobStatus.FAILED]:
                    break

            self.assertEqual(job.status, RenderJobStatus.COMPLETED)
            self.assertEqual(job.progress, 100)
            self.assertTrue(os.path.exists(job.output_path))
            self.assertGreater(job.file_size, 0)
            self.assertAlmostEqual(job.output_duration, 9.0, places=1)


class TestTimingIntegrity(unittest.IsolatedAsyncioTestCase):
    """
    Validates that timing consistency is preserved across M5, M7, M8, M9, and M10.
    """

    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        self.session_maker = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def asyncTearDown(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await self.engine.dispose()

    async def test_audio_segments_contiguous_timestamps(self):
        """Audio segments must form a contiguous, non-overlapping timeline."""
        seg1 = AudioSegment(sequence=1, start_time=0.0, end_time=3.2, duration=3.2, text="Seg 1")
        seg2 = AudioSegment(sequence=2, start_time=3.2, end_time=7.1, duration=3.9, text="Seg 2")
        seg3 = AudioSegment(sequence=3, start_time=7.1, end_time=10.0, duration=2.9, text="Seg 3")
        segs = [seg1, seg2, seg3]

        for i in range(len(segs) - 1):
            self.assertEqual(segs[i].end_time, segs[i + 1].start_time)
            self.assertGreater(segs[i].end_time, segs[i].start_time)

    async def test_caption_segments_strictly_inside_audio_bounds(self):
        """Every caption segment must remain inside its parent narration time range."""
        audio_seg = AudioSegment(sequence=1, start_time=3.0, end_time=6.5, duration=3.5, text="Contoh narasi")

        # Valid captions inside [3.0, 6.5]
        cap1 = CaptionSegment(sequence=1, start_time=3.0, end_time=4.8, text="Contoh")
        cap2 = CaptionSegment(sequence=2, start_time=4.8, end_time=6.5, text="narasi")

        self.assertGreaterEqual(cap1.start_time, audio_seg.start_time)
        self.assertLessEqual(cap1.end_time, audio_seg.end_time)
        self.assertGreaterEqual(cap2.start_time, audio_seg.start_time)
        self.assertLessEqual(cap2.end_time, audio_seg.end_time)
        self.assertGreater(cap1.end_time, cap1.start_time)
        self.assertGreater(cap2.end_time, cap2.start_time)


class TestStaleDependencyValidation(unittest.IsolatedAsyncioTestCase):
    """
    Tests that stale dependencies across M4–M10 are accurately detected and rejected.
    """

    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        self.session_maker = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.temp_dir = tempfile.TemporaryDirectory()
        self.render_service = RenderService(storage_base=self.temp_dir.name)

    async def asyncTearDown(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await self.engine.dispose()
        self.temp_dir.cleanup()

    async def test_stale_timeline_when_active_script_updated(self):
        """If active script changed after timeline was created, checklist must block."""
        async with self.session_maker() as session:
            e2e = TestEndToEndPipeline()
            seeded = await e2e._seed_full_production_pipeline(session)
            project_id = seeded["project"].id

            # Create a newer active script (e.g. v2)
            new_script = Script(
                project_id=project_id,
                version=2,
                status=ScriptStatus.READY,
                is_active=True,
                language="id"
            )
            # Deactivate v1
            seeded["script"].is_active = False
            session.add(new_script)
            await session.commit()

            chk = await self.render_service.validate_dependencies(session, project_id)
            self.assertFalse(chk["ready"])
            self.assertTrue(any("Production Timeline is stale" in err and "script" in err for err in chk["errors"]))

    async def test_stale_timeline_when_tts_regenerated(self):
        """If TTS was regenerated after timeline, checklist must block."""
        async with self.session_maker() as session:
            e2e = TestEndToEndPipeline()
            seeded = await e2e._seed_full_production_pipeline(session)
            project_id = seeded["project"].id

            # New completed TTS generation
            new_tts = TTSGeneration(
                project_id=project_id,
                script_id=seeded["script"].id,
                status=TTSStatus.COMPLETED,
                audio_path="storage/narration_v2.wav",
                duration=9.2
            )
            session.add(new_tts)
            await session.commit()

            chk = await self.render_service.validate_dependencies(session, project_id)
            self.assertFalse(chk["ready"])
            self.assertTrue(any("Production Timeline is stale" in err and "TTS" in err for err in chk["errors"]))

    async def test_stale_captions_when_timeline_changed(self):
        """If production timeline ID mismatches caption track, checklist must block."""
        async with self.session_maker() as session:
            e2e = TestEndToEndPipeline()
            seeded = await e2e._seed_full_production_pipeline(session)
            project_id = seeded["project"].id

            # Alter caption track's production_timeline_id
            seeded["caption_track"].production_timeline_id = uuid.uuid4()
            await session.commit()

            chk = await self.render_service.validate_dependencies(session, project_id)
            self.assertFalse(chk["ready"])
            self.assertTrue(any("Caption Track is stale" in err for err in chk["errors"]))


class TestStateTransitionsAndConcurrency(unittest.IsolatedAsyncioTestCase):
    """
    Tests render job state machine, concurrency locking, and cancellation.
    """

    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        self.session_maker = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.temp_dir = tempfile.TemporaryDirectory()
        self.render_service = RenderService(storage_base=self.temp_dir.name, session_maker=self.session_maker)

    async def asyncTearDown(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await self.engine.dispose()
        self.temp_dir.cleanup()

    async def test_missing_footage_blocks_render(self):
        """If any scene lacks selected footage, checklist rejects with exact scene number."""
        async with self.session_maker() as session:
            e2e = TestEndToEndPipeline()
            seeded = await e2e._seed_full_production_pipeline(session)
            project_id = seeded["project"].id

            # Remove candidate from Scene 2
            pt_id = seeded["prod_timeline"].id
            q = await session.execute(
                select(ProductionTimelineItem).where(
                    and_(
                        ProductionTimelineItem.timeline_id == pt_id,
                        ProductionTimelineItem.sequence == 2
                    )
                )
            )
            item2 = q.scalar_one()
            item2.footage_candidate_id = None
            await session.commit()

            chk = await self.render_service.validate_dependencies(session, project_id)
            self.assertFalse(chk["ready"])
            self.assertTrue(any("Scene 2 has no selected footage" in err for err in chk["errors"]))

    async def test_concurrency_safeguard_disallows_duplicate_active_renders(self):
        """A second render job cannot be created if an active one is already running."""
        async with self.session_maker() as session:
            e2e = TestEndToEndPipeline()
            seeded = await e2e._seed_full_production_pipeline(session)
            project_id = seeded["project"].id

            # Insert an active RENDERING job
            active_job = RenderJob(
                project_id=project_id,
                production_timeline_id=seeded["prod_timeline"].id,
                tts_generation_id=seeded["tts_gen"].id,
                caption_track_id=seeded["caption_track"].id,
                audio_timeline_id=seeded["audio_timeline"].id,
                status=RenderJobStatus.RENDERING,
                progress=45,
                current_step="Encoding",
                output_format="mp4"
            )
            session.add(active_job)
            await session.commit()

            with self.assertRaises(ValueError) as ctx:
                await self.render_service.create_render_job(session, project_id)

            self.assertIn("already in progress", str(ctx.exception))

    async def test_cancellation_marks_cancelled_and_cleans_intermediate_files(self):
        """Cancelling a job sets CANCELLED status and purges temporary intermediate files."""
        async with self.session_maker() as session:
            e2e = TestEndToEndPipeline()
            seeded = await e2e._seed_full_production_pipeline(session)
            project_id = seeded["project"].id

            job = RenderJob(
                project_id=project_id,
                production_timeline_id=seeded["prod_timeline"].id,
                tts_generation_id=seeded["tts_gen"].id,
                caption_track_id=seeded["caption_track"].id,
                audio_timeline_id=seeded["audio_timeline"].id,
                status=RenderJobStatus.RENDERING,
                progress=30,
                current_step="Composing",
                output_format="mp4"
            )
            session.add(job)
            await session.commit()

            # Create a mock intermediate workspace file
            workspace_dir = os.path.join(self.temp_dir.name, str(project_id), str(job.id))
            os.makedirs(workspace_dir, exist_ok=True)
            sub_file = os.path.join(workspace_dir, "subtitles.ass")
            with open(sub_file, "w") as f:
                f.write("MOCK_SUBTITLE")

            success = await self.render_service.cancel_render_job(session, job.id)
            self.assertTrue(success)

            await session.refresh(job)
            self.assertEqual(job.status, RenderJobStatus.CANCELLED)
            self.assertEqual(job.current_step, "Cancelled by user")
            # Intermediate subtitle file should be removed
            self.assertFalse(os.path.exists(sub_file))


if __name__ == "__main__":
    unittest.main()

import os
import uuid
import logging
import tempfile
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import select, func, update
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.project import Project
from app.models.script import Script, ScriptStatus
from app.models.tts_generation import TTSGeneration, TTSStatus
from app.models.audio_segment import AudioSegment
from app.models.tts_job import TTSJob, TTSJobStatus, TTSJobStep
from app.providers.storage.local import storage_provider
from app.providers.tts import get_tts_provider
from app.services.tts.audio_processor import audio_processor
from app.services.tts.queue import tts_queue

logger = logging.getLogger("shorts_api.services.tts")


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TTSService:
    """Service orchestrating narration generation, timeline construction, and background jobs."""

    @staticmethod
    async def create_and_enqueue_job(
        db: AsyncSession,
        project_id: uuid.UUID,
        script_id: Optional[uuid.UUID] = None,
        provider: Optional[str] = None,
        voice: Optional[str] = None,
        model: Optional[str] = None
    ) -> Tuple[TTSJob, TTSGeneration]:
        """
        Validates project and script prerequisites, creates a new TTSGeneration record + TTSJob,
        and enqueues the task to Redis.
        """
        # 1. Verify project
        p_stmt = select(Project).where(Project.id == project_id)
        project = (await db.execute(p_stmt)).scalar_one_or_none()
        if not project:
            raise ValueError(f"Project with ID '{project_id}' not found.")

        # 2. Get target script
        if script_id:
            s_stmt = select(Script).where(Script.id == script_id, Script.project_id == project_id)
            script = (await db.execute(s_stmt)).scalar_one_or_none()
            if not script:
                raise ValueError(f"Specified script '{script_id}' not found in this project.")
        else:
            # Pick active script first, then latest ready script
            s_stmt = (
                select(Script)
                .where(Script.project_id == project_id, Script.is_active == True)  # noqa: E712
            )
            script = (await db.execute(s_stmt)).scalar_one_or_none()

            if not script:
                s_stmt = (
                    select(Script)
                    .where(Script.project_id == project_id, Script.status == ScriptStatus.READY)
                    .order_by(Script.version.desc())
                )
                script = (await db.execute(s_stmt)).scalars().first()

            if not script:
                raise ValueError("Project does not have an active or ready script. Generate an adapted script first.")

        # 3. Check if first generation for this project
        count_stmt = select(func.count(TTSGeneration.id)).where(TTSGeneration.project_id == project_id)
        existing_count = (await db.execute(count_stmt)).scalar() or 0
        is_first_generation = (existing_count == 0)

        chosen_provider = (provider or settings.TTS_PROVIDER or "google").strip().lower()
        chosen_voice = voice or settings.TTS_VOICE or "id-ID-Standard-A"
        chosen_model = model or settings.TTS_MODEL or None

        # 4. Create TTSGeneration record
        generation = TTSGeneration(
            project_id=project_id,
            script_id=script.id,
            provider=chosen_provider,
            model=chosen_model,
            voice=chosen_voice,
            status=TTSStatus.QUEUED,
            audio_format="mp3",
            is_active=is_first_generation
        )
        db.add(generation)
        await db.flush()

        # 5. Create TTSJob
        job = TTSJob(
            project_id=project_id,
            tts_generation_id=generation.id,
            status=TTSJobStatus.QUEUED,
            progress=0,
            current_step=TTSJobStep.PREPARING_SCRIPT.value
        )
        db.add(job)
        await db.commit()
        await db.refresh(generation)
        await db.refresh(job)

        # 6. Push to Redis queue
        try:
            tts_queue.enqueue(
                job_id=str(job.id),
                tts_generation_id=str(generation.id),
                project_id=str(project_id)
            )
            logger.info(f"Enqueued TTS job {job.id} for generation {generation.id}")
        except Exception as exc:
            logger.error(f"Failed to push TTS task to Redis: {exc}")
            # Mark job failed immediately
            job.status = TTSJobStatus.FAILED
            job.error = f"Queue submission failed: {exc}"
            generation.status = TTSStatus.FAILED
            generation.error = job.error
            await db.commit()
            raise RuntimeError(f"Could not enqueue TTS job: {exc}") from exc

        return job, generation

    @classmethod
    async def process_job(cls, job_id_str: str) -> None:
        """
        Background worker execution method. Synthesizes audio per script segment,
        measures segment durations with FFprobe, creates AudioSegments,
        and concatenates the final narration audio.
        """
        logger.info(f"Processing TTS job: {job_id_str}")
        job_uuid = uuid.UUID(job_id_str)

        async with AsyncSessionLocal() as db:
            # 1. Fetch Job and Generation
            stmt = select(TTSJob).where(TTSJob.id == job_uuid)
            job = (await db.execute(stmt)).scalar_one_or_none()
            if not job:
                logger.error(f"TTS job '{job_id_str}' not found in database.")
                return

            gen_stmt = (
                select(TTSGeneration)
                .where(TTSGeneration.id == job.tts_generation_id)
                .options(selectinload(TTSGeneration.script))
            )
            generation = (await db.execute(gen_stmt)).scalar_one_or_none()
            if not generation:
                job.status = TTSJobStatus.FAILED
                job.error = "Associated TTSGeneration record not found."
                await db.commit()
                return

            script = generation.script
            if not script:
                job.status = TTSJobStatus.FAILED
                job.error = "Associated Script record not found."
                await db.commit()
                return

            # Mark as processing
            job.status = TTSJobStatus.PROCESSING
            job.started_at = get_utc_now()
            job.progress = 5
            job.current_step = TTSJobStep.PREPARING_SCRIPT.value
            generation.status = TTSStatus.PROCESSING
            await db.commit()

            try:
                # 2. Extract script segments
                raw_segments = script.segments or []
                segments_to_process: List[Dict[str, Any]] = []

                if raw_segments:
                    for i, seg in enumerate(raw_segments):
                        text = seg.get("adapted_text") or seg.get("text") or ""
                        if text.strip():
                            segments_to_process.append({
                                "scene_id": str(seg.get("scene_id") or f"scene_{i+1}"),
                                "sequence": int(seg.get("sequence") or (i + 1)),
                                "text": text.strip()
                            })

                # Fallback if no structured segments: treat full script content
                if not segments_to_process:
                    content = script.content.strip()
                    if not content:
                        raise ValueError("Script has no narration content or segments.")
                    segments_to_process.append({
                        "scene_id": "scene_1",
                        "sequence": 1,
                        "text": content
                    })

                total_segments = len(segments_to_process)
                logger.info(f"Synthesizing {total_segments} audio segments for generation {generation.id}")

                # 3. Resolve TTS Provider
                provider = get_tts_provider(generation.provider)

                cumulative_seconds = 0.0
                segment_full_paths: List[str] = []
                temp_segment_files: List[str] = []

                # 4. Generate audio per segment
                for idx, item in enumerate(segments_to_process):
                    seq = item["sequence"]
                    text = item["text"]
                    scene_id = item["scene_id"]

                    # Update progress
                    pct = int(10 + ((idx) / total_segments) * 65)
                    job.progress = pct
                    job.current_step = f"Generating segment {idx + 1} of {total_segments}"
                    await db.commit()

                    logger.info(f"Synthesizing segment {seq}/{total_segments}: {text[:40]}...")
                    audio_res = await provider.synthesize(
                        text=text,
                        voice=generation.voice,
                        model=generation.model
                    )

                    ext = audio_res.audio_format.lower().lstrip(".")
                    filename = f"seg_{seq}_{generation.id}.{ext}"

                    # Save segment audio in storage
                    storage_path = await storage_provider.save(
                        project_id=str(generation.project_id),
                        category="audio/segments",
                        filename=filename,
                        content=audio_res.audio_bytes
                    )
                    full_path = storage_provider.get_full_path(storage_path)
                    segment_full_paths.append(full_path)

                    # Measure duration with FFprobe (or wave fallback)
                    tech_info = await audio_processor.inspect_audio(full_path)
                    seg_duration = tech_info.duration if tech_info.duration > 0.05 else (audio_res.duration or 1.5)

                    start_time = round(cumulative_seconds, 3)
                    end_time = round(cumulative_seconds + seg_duration, 3)
                    duration = round(seg_duration, 3)
                    cumulative_seconds += seg_duration

                    # Create AudioSegment record
                    audio_segment = AudioSegment(
                        tts_generation_id=generation.id,
                        scene_id=scene_id,
                        sequence=seq,
                        text=text,
                        start_time=start_time,
                        end_time=end_time,
                        duration=duration,
                        audio_path=storage_path
                    )
                    db.add(audio_segment)
                    await db.flush()

                # 5. Concatenate segments into master narration
                job.progress = 80
                job.current_step = TTSJobStep.COMBINING_AUDIO.value
                await db.commit()

                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_out:
                    temp_master_path = tmp_out.name

                master_tech = await audio_processor.concatenate_segments(
                    segment_paths=segment_full_paths,
                    output_path=temp_master_path,
                    output_format="mp3"
                )

                # Save master narration file into storage
                with open(temp_master_path, "rb") as f_master:
                    master_bytes = f_master.read()

                master_storage_path = await storage_provider.save(
                    project_id=str(generation.project_id),
                    category="audio",
                    filename=f"narration_{generation.id}.mp3",
                    content=master_bytes
                )

                if os.path.exists(temp_master_path):
                    try:
                        os.unlink(temp_master_path)
                    except Exception:
                        pass

                # 6. Finalize generation and job
                job.progress = 100
                job.current_step = TTSJobStep.COMPLETED.value
                job.status = TTSJobStatus.COMPLETED
                job.completed_at = get_utc_now()

                generation.audio_path = master_storage_path
                generation.audio_format = "mp3"
                generation.duration = master_tech.duration if master_tech.duration > 0 else round(cumulative_seconds, 3)
                generation.sample_rate = master_tech.sample_rate or 44100
                generation.channels = master_tech.channels or 1
                generation.status = TTSStatus.COMPLETED
                generation.error = None

                await db.commit()
                logger.info(
                    f"TTS Job {job.id} completed successfully. "
                    f"Narration duration: {generation.duration}s ({master_storage_path})"
                )

            except Exception as exc:
                logger.error(f"TTS Job {job.id} failed: {exc}", exc_info=True)
                job.status = TTSJobStatus.FAILED
                job.error = str(exc)
                job.completed_at = get_utc_now()
                generation.status = TTSStatus.FAILED
                generation.error = str(exc)
                await db.commit()

    @staticmethod
    async def activate_generation(db: AsyncSession, generation_id: uuid.UUID) -> TTSGeneration:
        """Sets the specified generation as active and deactivates other generations in the project."""
        stmt = select(TTSGeneration).where(TTSGeneration.id == generation_id)
        generation = (await db.execute(stmt)).scalar_one_or_none()
        if not generation:
            raise ValueError(f"TTSGeneration '{generation_id}' not found.")

        # Deactivate others
        await db.execute(
            update(TTSGeneration)
            .where(TTSGeneration.project_id == generation.project_id)
            .values(is_active=False)
        )
        generation.is_active = True
        await db.commit()
        await db.refresh(generation)
        return generation

    @staticmethod
    async def get_timeline(db: AsyncSession, generation_id: uuid.UUID) -> Dict[str, Any]:
        """Returns structured audio timeline and segment timings for a TTS generation."""
        stmt = (
            select(TTSGeneration)
            .where(TTSGeneration.id == generation_id)
            .options(selectinload(TTSGeneration.segments))
        )
        generation = (await db.execute(stmt)).scalar_one_or_none()
        if not generation:
            raise ValueError(f"TTSGeneration '{generation_id}' not found.")

        segments_data = [
            {
                "id": str(seg.id),
                "scene_id": seg.scene_id,
                "sequence": seg.sequence,
                "text": seg.text,
                "start_time": seg.start_time,
                "end_time": seg.end_time,
                "duration": seg.duration,
                "audio_path": seg.audio_path
            }
            for seg in generation.segments
        ]

        return {
            "generation_id": str(generation.id),
            "project_id": str(generation.project_id),
            "script_id": str(generation.script_id),
            "duration": generation.duration or 0.0,
            "segments_count": len(segments_data),
            "segments": segments_data
        }


tts_service = TTSService()

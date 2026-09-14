import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import select, func, update
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.project import Project, ProjectStatus
from app.models.media_asset import MediaAsset
from app.models.transcript import Transcript
from app.models.scene import Scene
from app.models.script import Script, ScriptStatus
from app.models.script_job import ScriptJob, ScriptJobStatus, ScriptJobStep
from app.providers.script import get_script_provider
from app.providers.script.base import (
    ScriptGenerationContext,
    SceneContextItem,
    GeneratedScriptPayload,
)
from app.services.script.queue import script_queue
from app.services.script.duration import (
    count_words,
    calculate_speaking_duration,
    calculate_duration_ratio,
)

logger = logging.getLogger("shorts_api.services.script")


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ScriptService:
    """Service orchestrating Indonesian script generation, background execution, and editing."""

    @staticmethod
    async def create_and_enqueue_job(
        db: AsyncSession,
        project_id: uuid.UUID,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        instructions: Optional[str] = None,
        source_transcript_id: Optional[uuid.UUID] = None
    ) -> Tuple[ScriptJob, Script]:
        """
        Validates project prerequisites, creates a new Script version + ScriptJob,
        and pushes task to Redis.
        """
        # 1. Verify project
        p_stmt = select(Project).where(Project.id == project_id)
        project = (await db.execute(p_stmt)).scalar_one_or_none()
        if not project:
            raise ValueError(f"Project with ID '{project_id}' not found.")

        # 2. Get transcript
        if source_transcript_id:
            t_stmt = select(Transcript).where(
                Transcript.id == source_transcript_id,
                Transcript.project_id == project_id
            )
            transcript = (await db.execute(t_stmt)).scalar_one_or_none()
            if not transcript:
                raise ValueError(f"Specified transcript '{source_transcript_id}' not found.")
        else:
            t_stmt = (
                select(Transcript)
                .where(Transcript.project_id == project_id)
                .order_by(Transcript.version.desc())
            )
            transcript = (await db.execute(t_stmt)).scalars().first()
            if not transcript:
                raise ValueError("Project does not have a transcript yet. Run reference video analysis first.")

        # 3. Check scenes
        s_stmt = select(Scene).where(Scene.project_id == project_id)
        scenes = (await db.execute(s_stmt)).scalars().all()
        if not scenes:
            raise ValueError("Project does not have detected scenes yet. Run reference video analysis first.")

        # 4. Determine next script version number
        v_stmt = select(func.max(Script.version)).where(Script.project_id == project_id)
        max_version = (await db.execute(v_stmt)).scalar()
        next_version = (max_version or 0) + 1
        is_first_script = (max_version is None or max_version == 0)

        chosen_provider = (provider or settings.SCRIPT_PROVIDER or "gemini").lower()

        # 5. Create Script record in 'generating' state
        script = Script(
            project_id=project_id,
            source_transcript_id=transcript.id,
            version=next_version,
            is_active=is_first_script,  # First version automatically marked active
            language="id",
            status=ScriptStatus.GENERATING,
            title=f"Skrip Shorts #{next_version} ({project.name})",
            content="",
            segments=[],
            generation_provider=chosen_provider,
            generation_model=model,
            instructions=instructions,
            is_manually_edited=False
        )
        db.add(script)
        await db.flush()

        # 6. Create ScriptJob record
        job = ScriptJob(
            project_id=project_id,
            script_id=script.id,
            status=ScriptJobStatus.QUEUED,
            progress=0,
            current_step=ScriptJobStep.PREPARING_TRANSCRIPT.value,
            started_at=get_utc_now()
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        await db.refresh(script)

        # 7. Enqueue to Redis
        script_queue.enqueue(
            job_id=str(job.id),
            script_id=str(script.id),
            project_id=str(project_id)
        )
        logger.info(f"Script adaptation job {job.id} enqueued for project {project_id} (version {next_version})")

        return job, script

    @staticmethod
    async def _update_job_progress(
        db: AsyncSession,
        job_id: uuid.UUID,
        progress: int,
        step: str,
        status: ScriptJobStatus = ScriptJobStatus.PROCESSING,
        error: Optional[str] = None
    ) -> None:
        stmt = select(ScriptJob).where(ScriptJob.id == job_id)
        job = (await db.execute(stmt)).scalar_one_or_none()
        if job:
            job.progress = progress
            job.current_step = step
            job.status = status
            job.error = error
            if status in (ScriptJobStatus.COMPLETED, ScriptJobStatus.FAILED):
                job.completed_at = get_utc_now()
            await db.commit()

    @staticmethod
    async def process_job(job_id: str) -> None:
        """
        Worker pipeline: loads transcript and scene context, queries provider,
        validates structured JSON output, calculates duration metrics, and persists.
        """
        job_uuid = uuid.UUID(job_id)
        logger.info(f"Starting execution of script adaptation job {job_id}")

        async with AsyncSessionLocal() as db:
            # 1. Load Job
            job_stmt = select(ScriptJob).where(ScriptJob.id == job_uuid)
            job = (await db.execute(job_stmt)).scalar_one_or_none()
            if not job:
                logger.error(f"Cannot process script job {job_id}: record not found.")
                return

            script_stmt = select(Script).where(Script.id == job.script_id)
            script = (await db.execute(script_stmt)).scalar_one_or_none()
            if not script:
                await ScriptService._update_job_progress(
                    db, job_uuid, 0, "failed", status=ScriptJobStatus.FAILED,
                    error="Associated Script record missing."
                )
                return

            try:
                # Step 1: Preparing transcript & scene context (0% -> 25%)
                await ScriptService._update_job_progress(
                    db, job_uuid, 25, ScriptJobStep.PREPARING_SCENE_CONTEXT.value
                )

                project_stmt = select(Project).where(Project.id == script.project_id)
                project = (await db.execute(project_stmt)).scalar_one()

                transcript_stmt = select(Transcript).where(Transcript.id == script.source_transcript_id)
                transcript = (await db.execute(transcript_stmt)).scalar_one()

                scenes_stmt = (
                    select(Scene)
                    .where(Scene.project_id == script.project_id)
                    .order_by(Scene.sequence.asc())
                )
                scenes = (await db.execute(scenes_stmt)).scalars().all()

                # Source duration from reference asset or total scene length
                source_duration = None
                if project.reference_asset_id:
                    asset_stmt = select(MediaAsset).where(MediaAsset.id == project.reference_asset_id)
                    ref_asset = (await db.execute(asset_stmt)).scalar_one_or_none()
                    if ref_asset and ref_asset.duration:
                        source_duration = ref_asset.duration

                if not source_duration and scenes:
                    source_duration = scenes[-1].end_time

                # Assemble scene context items for LLM
                scene_items: List[SceneContextItem] = []
                for sc in scenes:
                    spoken_text = " ".join(
                        seg.get("text", "").strip() for seg in sc.transcript_segment if seg.get("text")
                    ) if sc.transcript_segment else ""

                    scene_items.append(
                        SceneContextItem(
                            scene_id=str(sc.id),
                            sequence=sc.sequence,
                            start_time=sc.start_time,
                            end_time=sc.end_time,
                            duration=sc.duration,
                            visual_description=sc.description,
                            source_dialogue=spoken_text or None
                        )
                    )

                gen_context = ScriptGenerationContext(
                    project_name=project.name,
                    source_language=transcript.language or "en",
                    target_language="id",
                    source_transcript_full=transcript.content,
                    scenes=scene_items,
                    instructions=script.instructions,
                    target_wpm=settings.SCRIPT_TARGET_WPM
                )

                # Step 2: Generating script with LLM (25% -> 60%)
                await ScriptService._update_job_progress(
                    db, job_uuid, 60, ScriptJobStep.GENERATING_SCRIPT.value
                )

                provider = get_script_provider(script.generation_provider, script.generation_model)
                generated_payload: GeneratedScriptPayload = await provider.generate_script(gen_context)

                # Step 3: Validating output & aligning segments (60% -> 80%)
                await ScriptService._update_job_progress(
                    db, job_uuid, 80, ScriptJobStep.VALIDATING_OUTPUT.value
                )

                # Map generated segments with scene timing and duration estimation
                segment_map = {str(seg.scene_id): seg for seg in generated_payload.segments}
                final_segments: List[Dict[str, Any]] = []

                for sc in scenes:
                    matched = segment_map.get(str(sc.id))
                    adapted_text = matched.adapted_text if matched else ""
                    if not adapted_text and matched is None:
                        # Fallback heuristic if LLM missed an exact scene ID
                        adapted_text = f"Lanjutan visual scene {sc.sequence}."

                    seg_words = count_words(adapted_text)
                    seg_est_duration = calculate_speaking_duration(adapted_text, settings.SCRIPT_TARGET_WPM)

                    source_dialogue = " ".join(
                        seg.get("text", "").strip() for seg in sc.transcript_segment if seg.get("text")
                    ) if sc.transcript_segment else ""

                    final_segments.append({
                        "scene_id": str(sc.id),
                        "sequence": sc.sequence,
                        "start_time": sc.start_time,
                        "end_time": sc.end_time,
                        "duration": sc.duration,
                        "visual_description": sc.description,
                        "source_text": source_dialogue,
                        "adapted_text": adapted_text,
                        "word_count": seg_words,
                        "estimated_duration": seg_est_duration
                    })

                # Step 4: Saving script & calculating metrics (80% -> 95%)
                await ScriptService._update_job_progress(
                    db, job_uuid, 95, ScriptJobStep.SAVING_SCRIPT.value
                )

                full_script = generated_payload.full_script.strip()
                if not full_script:
                    full_script = " ".join(s["adapted_text"] for s in final_segments)

                total_words = count_words(full_script)
                total_est_duration = calculate_speaking_duration(full_script, settings.SCRIPT_TARGET_WPM)
                duration_ratio = calculate_duration_ratio(total_est_duration, source_duration)

                script.title = generated_payload.title.strip()
                script.content = full_script
                script.segments = final_segments
                script.word_count = total_words
                script.estimated_duration = total_est_duration
                script.source_duration = source_duration
                script.duration_ratio = duration_ratio
                script.status = ScriptStatus.READY
                script.error = None
                script.updated_at = get_utc_now()

                # Step 5: Completed (100%)
                await ScriptService._update_job_progress(
                    db, job_uuid, 100, ScriptJobStep.COMPLETED.value,
                    status=ScriptJobStatus.COMPLETED
                )
                await db.commit()
                logger.info(f"Script adaptation job {job_id} successfully completed (Script {script.id})")

            except Exception as exc:
                logger.error(f"Script adaptation job {job_id} failed: {exc}", exc_info=True)
                await db.rollback()
                script.status = ScriptStatus.FAILED
                script.error = str(exc)
                await ScriptService._update_job_progress(
                    db, job_uuid, 0, "failed",
                    status=ScriptJobStatus.FAILED,
                    error=str(exc)
                )
                await db.commit()

    @staticmethod
    async def get_script(db: AsyncSession, script_id: uuid.UUID) -> Script:
        """Retrieves a script by ID."""
        stmt = select(Script).where(Script.id == script_id)
        script = (await db.execute(stmt)).scalar_one_or_none()
        if not script:
            raise ValueError(f"Script with ID '{script_id}' not found.")
        return script

    @staticmethod
    async def list_project_scripts(db: AsyncSession, project_id: uuid.UUID) -> List[Script]:
        """Lists all script versions for a project ordered by version descending."""
        stmt = (
            select(Script)
            .where(Script.project_id == project_id)
            .order_by(Script.version.desc())
        )
        return list((await db.execute(stmt)).scalars().all())

    @staticmethod
    async def update_script(
        db: AsyncSession,
        script_id: uuid.UUID,
        title: Optional[str] = None,
        content: Optional[str] = None,
        segments: Optional[List[Dict[str, Any]]] = None
    ) -> Script:
        """
        Manually modifies an existing script. Does NOT call AI.
        Recalculates speaking duration and duration ratio, marks is_manually_edited=True.
        """
        stmt = select(Script).where(Script.id == script_id)
        script = (await db.execute(stmt)).scalar_one_or_none()
        if not script:
            raise ValueError(f"Script with ID '{script_id}' not found.")

        if title is not None:
            script.title = title.strip()

        if segments is not None:
            # Recalculate word count and estimated duration for each updated segment
            enriched_segments = []
            for seg in segments:
                adapted = seg.get("adapted_text", "").strip()
                seg_words = count_words(adapted)
                seg_dur = calculate_speaking_duration(adapted, settings.SCRIPT_TARGET_WPM)
                enriched = dict(seg)
                enriched["word_count"] = seg_words
                enriched["estimated_duration"] = seg_dur
                enriched_segments.append(enriched)
            script.segments = enriched_segments

            # If full content was not explicitly passed, reconstruct from segments
            if content is None:
                script.content = " ".join(s.get("adapted_text", "") for s in enriched_segments)

        if content is not None:
            script.content = content.strip()

        # Recalculate overall metrics
        script.word_count = count_words(script.content)
        script.estimated_duration = calculate_speaking_duration(script.content, settings.SCRIPT_TARGET_WPM)
        script.duration_ratio = calculate_duration_ratio(script.estimated_duration, script.source_duration)
        script.is_manually_edited = True
        script.updated_at = get_utc_now()

        await db.commit()
        await db.refresh(script)
        logger.info(f"Script {script_id} manually updated (new duration: {script.estimated_duration}s)")
        return script

    @staticmethod
    async def activate_script(db: AsyncSession, script_id: uuid.UUID) -> Script:
        """
        Marks a specific script version as active and deactivates all other versions for the project.
        """
        stmt = select(Script).where(Script.id == script_id)
        target = (await db.execute(stmt)).scalar_one_or_none()
        if not target:
            raise ValueError(f"Script with ID '{script_id}' not found.")

        # Deactivate all other versions in the same project
        deactivate_stmt = (
            update(Script)
            .where(Script.project_id == target.project_id)
            .values(is_active=False)
        )
        await db.execute(deactivate_stmt)

        # Activate target script
        target.is_active = True
        target.updated_at = get_utc_now()

        await db.commit()
        await db.refresh(target)
        logger.info(f"Script {script_id} (v{target.version}) marked as active for project {target.project_id}")
        return target


script_service = ScriptService()

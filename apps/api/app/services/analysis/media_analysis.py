import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.project import Project, ProjectStatus
from app.models.media_asset import MediaAsset, MediaAssetType
from app.models.transcript import Transcript
from app.models.scene import Scene
from app.models.keyframe import Keyframe
from app.models.analysis_job import AnalysisJob, AnalysisJobStatus, AnalysisJobStep
from app.providers.storage.local import storage_provider

from app.services.analysis.audio_extraction import audio_extraction_service
from app.services.analysis.transcription import get_stt_provider
from app.services.analysis.scene_detection import scene_detection_service
from app.services.analysis.keyframe_extraction import keyframe_extraction_service
from app.services.analysis.scene_description import get_vision_provider
from app.services.analysis.queue import analysis_queue

logger = logging.getLogger("shorts_api.services.media_analysis")


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ReferenceAnalysisService:
    """Orchestrator for reference video analysis pipeline."""

    @staticmethod
    async def create_and_enqueue_job(
        db: AsyncSession,
        project_id: uuid.UUID,
        reanalyze: bool = False
    ) -> AnalysisJob:
        """
        Creates an AnalysisJob record in database and enqueues task to Redis.
        """
        # Validate project and reference video
        project_stmt = select(Project).where(Project.id == project_id)
        res = await db.execute(project_stmt)
        project = res.scalar_one_or_none()
        if not project:
            raise ValueError(f"Project '{project_id}' not found.")

        if not project.reference_asset_id:
            raise ValueError("Project does not have a reference video uploaded yet.")

        # Check existing completed analysis unless reanalyze is requested
        if not reanalyze:
            existing_t_stmt = select(Transcript).where(Transcript.project_id == project_id)
            existing_t = (await db.execute(existing_t_stmt)).scalar_one_or_none()
            if existing_t:
                # Check if there is an existing completed job
                job_stmt = select(AnalysisJob).where(
                    AnalysisJob.project_id == project_id,
                    AnalysisJob.status == AnalysisJobStatus.COMPLETED
                ).order_by(AnalysisJob.created_at.desc())
                existing_job = (await db.execute(job_stmt)).scalars().first()
                if existing_job:
                    logger.info(f"Project {project_id} already has completed analysis. Reusing job {existing_job.id}.")
                    return existing_job

        # Create new AnalysisJob record
        job = AnalysisJob(
            project_id=project_id,
            status=AnalysisJobStatus.QUEUED,
            progress=0,
            current_step=AnalysisJobStep.INITIALIZING.value,
            started_at=get_utc_now()
        )
        db.add(job)

        # Update project status to analyzing
        project.status = ProjectStatus.ANALYZING
        await db.commit()
        await db.refresh(job)

        # Enqueue to Redis
        analysis_queue.enqueue(str(job.id), str(project_id), reanalyze=reanalyze)
        logger.info(f"Analysis job {job.id} created and enqueued for project {project_id}")
        return job

    @staticmethod
    async def _update_job_progress(
        db: AsyncSession,
        job_id: uuid.UUID,
        progress: int,
        step: str,
        status: AnalysisJobStatus = AnalysisJobStatus.PROCESSING,
        error: Optional[str] = None
    ) -> None:
        stmt = select(AnalysisJob).where(AnalysisJob.id == job_id)
        res = await db.execute(stmt)
        job = res.scalar_one_or_none()
        if job:
            job.progress = progress
            job.current_step = step
            job.status = status
            job.error = error
            if status == AnalysisJobStatus.COMPLETED:
                job.completed_at = get_utc_now()
            elif status == AnalysisJobStatus.FAILED:
                job.completed_at = get_utc_now()
            await db.commit()

    @staticmethod
    async def process_job(job_id: str) -> None:
        """
        Main execution pipeline executed by the worker.
        Runs full reference video analysis with progress updates.
        """
        job_uuid = uuid.UUID(job_id)
        temp_audio_path = None

        async with AsyncSessionLocal() as db:
            job_stmt = select(AnalysisJob).where(AnalysisJob.id == job_uuid)
            job = (await db.execute(job_stmt)).scalar_one_or_none()
            if not job:
                logger.error(f"Cannot process job {job_id}: record not found in database.")
                return

            project_id = job.project_id
            project_stmt = select(Project).where(Project.id == project_id)
            project = (await db.execute(project_stmt)).scalar_one_or_none()
            if not project or not project.reference_asset_id:
                await ReferenceAnalysisService._update_job_progress(
                    db, job_uuid, 0, "failed",
                    status=AnalysisJobStatus.FAILED,
                    error="Project or reference video asset not found."
                )
                return

            asset_stmt = select(MediaAsset).where(MediaAsset.id == project.reference_asset_id)
            reference_asset = (await db.execute(asset_stmt)).scalar_one_or_none()
            if not reference_asset:
                await ReferenceAnalysisService._update_job_progress(
                    db, job_uuid, 0, "failed",
                    status=AnalysisJobStatus.FAILED,
                    error="Reference media asset file record is missing."
                )
                return

            video_full_path = storage_provider.get_full_path(reference_asset.storage_path)
            if not os.path.exists(video_full_path):
                await ReferenceAnalysisService._update_job_progress(
                    db, job_uuid, 0, "failed",
                    status=AnalysisJobStatus.FAILED,
                    error=f"Reference video file missing on disk: {reference_asset.storage_path}"
                )
                return

            try:
                # Step 0: Initializing
                logger.info(f"[{job_id}] Step 0: Initializing analysis for project {project_id}")
                await ReferenceAnalysisService._update_job_progress(
                    db, job_uuid, 5, AnalysisJobStep.INITIALIZING.value
                )

                # Step 1: Extract Audio (0% -> 15%)
                logger.info(f"[{job_id}] Step 1: Extracting audio from {video_full_path}")
                await ReferenceAnalysisService._update_job_progress(
                    db, job_uuid, 15, AnalysisJobStep.EXTRACTING_AUDIO.value
                )
                temp_audio_path = await audio_extraction_service.extract_audio(video_full_path)

                # Step 2: Transcribe (15% -> 35%)
                logger.info(f"[{job_id}] Step 2: Transcribing audio with STT provider")
                await ReferenceAnalysisService._update_job_progress(
                    db, job_uuid, 35, AnalysisJobStep.TRANSCRIBING.value
                )
                stt_provider = get_stt_provider()
                stt_result = await stt_provider.transcribe(temp_audio_path)

                # Step 3: Detect Scenes (35% -> 55%)
                logger.info(f"[{job_id}] Step 3: Detecting scene transitions")
                await ReferenceAnalysisService._update_job_progress(
                    db, job_uuid, 55, AnalysisJobStep.DETECTING_SCENES.value
                )
                video_duration = reference_asset.duration or 10.0
                raw_scenes = await scene_detection_service.detect_scenes(
                    video_path=video_full_path,
                    total_duration=video_duration
                )
                aligned_scenes = scene_detection_service.align_transcript(
                    scenes_raw=raw_scenes,
                    segments=stt_result.segments
                )

                # Prepare Database Cleanup for Reanalysis if old records exist
                old_keyframes_stmt = select(Keyframe).join(Scene).where(Scene.project_id == project_id)
                old_keyframes = (await db.execute(old_keyframes_stmt)).scalars().all()
                for old_kf in old_keyframes:
                    try:
                        await storage_provider.delete(old_kf.image_path)
                    except Exception:
                        pass

                await db.execute(delete(Scene).where(Scene.project_id == project_id))
                await db.execute(delete(Transcript).where(Transcript.project_id == project_id))
                await db.commit()

                # Step 4: Persist Transcript
                transcript_record = Transcript(
                    project_id=project_id,
                    media_asset_id=reference_asset.id,
                    language=stt_result.language,
                    provider=stt_result.provider,
                    content=stt_result.text,
                    segments=[s.model_dump() for s in stt_result.segments],
                    version=1
                )
                db.add(transcript_record)
                await db.flush()

                # Step 5: Extract Keyframes (55% -> 70%)
                logger.info(f"[{job_id}] Step 5: Extracting keyframes for {len(aligned_scenes)} scenes")
                await ReferenceAnalysisService._update_job_progress(
                    db, job_uuid, 70, AnalysisJobStep.EXTRACTING_KEYFRAMES.value
                )

                vision_provider = get_vision_provider()
                created_scenes: List[Scene] = []

                for sc in aligned_scenes:
                    scene_record = Scene(
                        project_id=project_id,
                        sequence=sc.sequence,
                        start_time=sc.start_time,
                        end_time=sc.end_time,
                        duration=sc.duration,
                        transcript_segment=sc.transcript_segments
                    )
                    db.add(scene_record)
                    await db.flush()

                    # Extract Keyframes
                    keyframes_data = await keyframe_extraction_service.extract_scene_keyframes(
                        video_path=video_full_path,
                        project_id=project_id,
                        scene_id=scene_record.id,
                        start_time=sc.start_time,
                        duration=sc.duration
                    )

                    keyframe_paths = []
                    for kf in keyframes_data:
                        kf_record = Keyframe(
                            scene_id=scene_record.id,
                            timestamp=kf.timestamp,
                            image_path=kf.image_path,
                            quality_score=kf.quality_score
                        )
                        db.add(kf_record)
                        keyframe_paths.append(storage_provider.get_full_path(kf.image_path))

                    created_scenes.append((scene_record, keyframe_paths, sc))

                await db.commit()

                # Step 6: Visual Descriptions (70% -> 90%)
                logger.info(f"[{job_id}] Step 6: Describing scenes with vision provider")
                await ReferenceAnalysisService._update_job_progress(
                    db, job_uuid, 90, AnalysisJobStep.DESCRIBING_SCENES.value
                )

                for scene_record, kf_paths, sc_data in created_scenes:
                    transcript_text = " ".join([seg.get("text", "") for seg in sc_data.transcript_segments])
                    description_res = await vision_provider.describe_scene(
                        keyframe_full_paths=kf_paths,
                        transcript_context=transcript_text
                    )
                    scene_record.description = description_res.description

                # Step 7: Finalize (100% -> Completed)
                project.status = ProjectStatus.READY
                await ReferenceAnalysisService._update_job_progress(
                    db, job_uuid, 100, AnalysisJobStep.FINALIZING.value,
                    status=AnalysisJobStatus.COMPLETED
                )
                await db.commit()
                logger.info(f"[{job_id}] Analysis completed successfully for project {project_id}")

            except Exception as exc:
                logger.error(f"[{job_id}] Analysis pipeline failed: {exc}", exc_info=True)
                await db.rollback()
                project.status = ProjectStatus.FAILED
                await ReferenceAnalysisService._update_job_progress(
                    db, job_uuid, 0, "failed",
                    status=AnalysisJobStatus.FAILED,
                    error=str(exc)
                )
            finally:
                # Cleanup temp audio
                audio_extraction_service.cleanup_file(temp_audio_path)


reference_analysis_service = ReferenceAnalysisService()

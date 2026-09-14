import uuid
import logging
from typing import List, Dict, Any, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import select, func, update
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.models.script import Script, ScriptStatus
from app.models.tts_generation import TTSGeneration, TTSStatus
from app.models.audio_segment import AudioSegment
from app.models.production_timeline import ProductionTimeline, ProductionTimelineItem
from app.models.scene import Scene
from app.models.caption import CaptionTrack, CaptionSegment, CaptionTrackStatus
from app.services.captions.caption_splitter import CaptionSplitter

logger = logging.getLogger("shorts_api.captions.service")


def format_srt_timestamp(seconds: float) -> str:
    """Formats float seconds into standard SubRip timestamp format: HH:MM:SS,mmm"""
    total_ms = int(round(max(0.0, seconds) * 1000))
    hours = total_ms // 3600000
    remainder = total_ms % 3600000
    minutes = remainder // 60000
    remainder = remainder % 60000
    secs = remainder // 1000
    millis = remainder % 1000
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


class CaptionGenerationService:
    """
    Orchestration service for generating, versioning, editing, and exporting
    renderer-ready timestamped captions (Milestone 8).
    """

    async def generate_captions(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        script_id: Optional[uuid.UUID] = None,
        tts_generation_id: Optional[uuid.UUID] = None,
        production_timeline_id: Optional[uuid.UUID] = None,
        target_words_per_segment: int = 4,
    ) -> Dict[str, Any]:
        """
        Builds a deterministic, versioned caption track from:
        - Active Indonesian Script (M4)
        - Completed TTS Audio Timeline (M5) -> PRIMARY TIMING SOURCE
        - Production Timeline (M7) -> Scene Mapping
        """
        # 1. Verify project exists
        proj_res = await db.execute(select(Project).where(Project.id == project_id))
        project = proj_res.scalar_one_or_none()
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")

        # 2. Resolve Script
        if script_id:
            s_res = await db.execute(
                select(Script).where(Script.id == script_id, Script.project_id == project_id)
            )
            script = s_res.scalar_one_or_none()
            if not script or script.status != ScriptStatus.READY:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Specified script was not found or is not in 'ready' status."
                )
        else:
            s_res = await db.execute(
                select(Script).where(
                    Script.project_id == project_id,
                    Script.is_active == True,
                    Script.status == ScriptStatus.READY
                )
            )
            script = s_res.scalar_one_or_none()
            if not script:
                s_res = await db.execute(
                    select(Script).where(
                        Script.project_id == project_id,
                        Script.status == ScriptStatus.READY
                    ).order_by(Script.version.desc())
                )
                script = s_res.scalars().first()
                if not script:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Active Indonesian script is required before generating captions. Complete Milestone 4 first."
                    )

        # 3. Resolve TTS Generation
        if tts_generation_id:
            t_res = await db.execute(
                select(TTSGeneration).where(
                    TTSGeneration.id == tts_generation_id,
                    TTSGeneration.project_id == project_id
                )
            )
            tts_gen = t_res.scalar_one_or_none()
            if not tts_gen or tts_gen.status != TTSStatus.COMPLETED:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Specified TTS generation was not found or is not completed."
                )
        else:
            t_res = await db.execute(
                select(TTSGeneration).where(
                    TTSGeneration.project_id == project_id,
                    TTSGeneration.is_active == True,
                    TTSGeneration.status == TTSStatus.COMPLETED
                )
            )
            tts_gen = t_res.scalar_one_or_none()
            if not tts_gen:
                t_res = await db.execute(
                    select(TTSGeneration).where(
                        TTSGeneration.project_id == project_id,
                        TTSGeneration.status == TTSStatus.COMPLETED
                    ).order_by(TTSGeneration.created_at.desc())
                )
                tts_gen = t_res.scalars().first()
                if not tts_gen:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Completed TTS narration audio is required before generating captions. Complete Milestone 5 first."
                    )

        # 4. Resolve Production Timeline
        if production_timeline_id:
            pt_res = await db.execute(
                select(ProductionTimeline).where(
                    ProductionTimeline.id == production_timeline_id,
                    ProductionTimeline.project_id == project_id
                )
            )
            timeline = pt_res.scalar_one_or_none()
            if not timeline:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Specified production timeline was not found."
                )
        else:
            pt_res = await db.execute(
                select(ProductionTimeline).where(
                    ProductionTimeline.project_id == project_id,
                    ProductionTimeline.is_active == True
                )
            )
            timeline = pt_res.scalar_one_or_none()
            if not timeline:
                pt_res = await db.execute(
                    select(ProductionTimeline).where(
                        ProductionTimeline.project_id == project_id
                    ).order_by(ProductionTimeline.version.desc())
                )
                timeline = pt_res.scalars().first()
                if not timeline:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Active production timeline is required before generating captions. Complete Milestone 7 first."
                    )

        # 5. Fetch Audio Segments (PRIMARY TIMING SOURCE)
        audio_segs_res = await db.execute(
            select(AudioSegment).where(
                AudioSegment.tts_generation_id == tts_gen.id
            ).order_by(AudioSegment.sequence.asc())
        )
        audio_segs = list(audio_segs_res.scalars().all())
        if not audio_segs:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selected TTS generation has no audio segments."
            )

        # 6. Fetch timeline items to help resolve scene mapping
        items_res = await db.execute(
            select(ProductionTimelineItem).where(
                ProductionTimelineItem.timeline_id == timeline.id
            ).order_by(ProductionTimelineItem.sequence.asc())
        )
        timeline_items = list(items_res.scalars().all())
        seq_to_scene_id = {it.sequence: it.scene_id for it in timeline_items}

        # 7. Calculate Next Version
        ver_res = await db.execute(
            select(func.max(CaptionTrack.version)).where(CaptionTrack.project_id == project_id)
        )
        current_max_ver = ver_res.scalar() or 0
        new_version = current_max_ver + 1

        # 8. Generate Caption Segments
        caption_segments: List[CaptionSegment] = []
        global_sequence = 1
        total_audio_duration = 0.0

        for audio_seg in audio_segs:
            text = (audio_seg.text or "").strip()
            if not text:
                continue

            seg_start = round(audio_seg.start_time, 2)
            seg_end = round(audio_seg.end_time, 2)
            seg_duration = max(0.05, round(seg_end - seg_start, 2))
            total_audio_duration = max(total_audio_duration, seg_end)

            # Resolve scene ID
            scene_uuid: Optional[uuid.UUID] = None
            if audio_seg.scene_id:
                try:
                    scene_uuid = uuid.UUID(str(audio_seg.scene_id))
                except (ValueError, TypeError):
                    pass
            if not scene_uuid:
                scene_uuid = seq_to_scene_id.get(audio_seg.sequence)

            # Split narration text into short readable caption chunks
            chunks = CaptionSplitter.split_text(
                text=text,
                target_words=target_words_per_segment,
                max_words=max(6, target_words_per_segment + 2)
            )
            if not chunks:
                chunks = [text]

            # Proportional timestamp distribution
            # Weights proportional to character count of each chunk
            weights = [max(1, len(re_clean := chunk.strip())) for chunk in chunks]
            total_weight = sum(weights)

            cursor_time = seg_start
            for idx, chunk in enumerate(chunks):
                is_last_chunk = (idx == len(chunks) - 1)

                if is_last_chunk:
                    chunk_start = cursor_time
                    chunk_end = seg_end
                else:
                    fraction = weights[idx] / float(total_weight)
                    chunk_dur = round(seg_duration * fraction, 2)
                    chunk_start = cursor_time
                    chunk_end = min(seg_end - 0.05, round(chunk_start + chunk_dur, 2))
                    if chunk_end <= chunk_start:
                        chunk_end = round(chunk_start + 0.1, 2)

                chunk_duration = max(0.01, round(chunk_end - chunk_start, 2))

                # Create segment entity
                c_seg = CaptionSegment(
                    sequence=global_sequence,
                    start_time=round(chunk_start, 2),
                    end_time=round(chunk_end, 2),
                    duration=chunk_duration,
                    text=chunk,
                    source_audio_segment_id=audio_seg.id,
                    scene_id=scene_uuid,
                    style="default",
                    position="bottom",
                )
                caption_segments.append(c_seg)
                global_sequence += 1
                cursor_time = chunk_end

        # 9. Deactivate previous tracks
        await db.execute(
            update(CaptionTrack)
            .where(CaptionTrack.project_id == project_id)
            .values(is_active=False)
        )

        # 10. Save CaptionTrack
        track = CaptionTrack(
            project_id=project_id,
            script_id=script.id,
            tts_generation_id=tts_gen.id,
            production_timeline_id=timeline.id,
            version=new_version,
            language=script.language or "id",
            status=CaptionTrackStatus.READY,
            total_duration=round(total_audio_duration, 2),
            total_segments=len(caption_segments),
            is_active=True,
            segments=caption_segments,
        )

        db.add(track)
        await db.commit()
        await db.refresh(track)

        logger.info(
            f"Created CaptionTrack v{new_version} for project {project_id} "
            f"({len(caption_segments)} segments, duration {total_audio_duration:.2f}s)"
        )

        return await self.get_caption_track(db, track.id)

    async def check_stale_status(
        self,
        db: AsyncSession,
        track: CaptionTrack
    ) -> Tuple[bool, List[str]]:
        """
        Detects whether this caption track is outdated due to:
        - Active script changes
        - Active TTS generation changes
        - Active production timeline changes
        """
        reasons: List[str] = []

        # 1. Script check
        s_res = await db.execute(
            select(Script.id).where(
                Script.project_id == track.project_id,
                Script.is_active == True,
                Script.status == ScriptStatus.READY
            )
        )
        active_s_id = s_res.scalar_one_or_none()
        if active_s_id and active_s_id != track.script_id:
            reasons.append("Active Indonesian script has changed since captions were generated.")

        # 2. TTS check
        t_res = await db.execute(
            select(TTSGeneration.id).where(
                TTSGeneration.project_id == track.project_id,
                TTSGeneration.is_active == True,
                TTSGeneration.status == TTSStatus.COMPLETED
            )
        )
        active_t_id = t_res.scalar_one_or_none()
        if active_t_id and active_t_id != track.tts_generation_id:
            reasons.append("Active TTS narration audio has changed since captions were generated.")

        # 3. Production Timeline check
        pt_res = await db.execute(
            select(ProductionTimeline.id).where(
                ProductionTimeline.project_id == track.project_id,
                ProductionTimeline.is_active == True
            )
        )
        active_pt_id = pt_res.scalar_one_or_none()
        if active_pt_id and active_pt_id != track.production_timeline_id:
            reasons.append("Active production timeline has changed since captions were generated.")

        is_stale = len(reasons) > 0
        return is_stale, reasons

    async def get_caption_track(
        self,
        db: AsyncSession,
        track_id: uuid.UUID
    ) -> Optional[Dict[str, Any]]:
        """Fetches detailed caption track with segments, stale status, and metrics."""
        query = (
            select(CaptionTrack)
            .options(
                selectinload(CaptionTrack.segments).joinedload(CaptionSegment.scene)
            )
            .where(CaptionTrack.id == track_id)
        )
        res = await db.execute(query)
        track = res.scalar_one_or_none()
        if not track:
            return None

        is_stale, stale_reasons = await self.check_stale_status(db, track)

        formatted_segments = []
        scenes_seen = set()
        durations = []

        for seg in track.segments:
            if seg.scene_id:
                scenes_seen.add(seg.scene_id)
            durations.append(seg.duration)

            formatted_segments.append({
                "id": seg.id,
                "caption_track_id": seg.caption_track_id,
                "sequence": seg.sequence,
                "start_time": seg.start_time,
                "end_time": seg.end_time,
                "duration": seg.duration,
                "text": seg.text,
                "source_audio_segment_id": seg.source_audio_segment_id,
                "scene_id": seg.scene_id,
                "scene_sequence": seg.scene.sequence if seg.scene else None,
                "style": seg.style,
                "position": seg.position,
                "created_at": seg.created_at,
                "updated_at": seg.updated_at,
            })

        avg_dur = round(sum(durations) / len(durations), 2) if durations else None

        return {
            "id": track.id,
            "project_id": track.project_id,
            "script_id": track.script_id,
            "tts_generation_id": track.tts_generation_id,
            "production_timeline_id": track.production_timeline_id,
            "version": track.version,
            "language": track.language,
            "status": track.status.value if hasattr(track.status, "value") else str(track.status),
            "total_duration": track.total_duration,
            "total_segments": track.total_segments,
            "is_active": track.is_active,
            "is_stale": is_stale,
            "stale_reasons": stale_reasons,
            "average_caption_duration": avg_dur,
            "scenes_covered": len(scenes_seen),
            "segments": formatted_segments,
            "created_at": track.created_at,
            "updated_at": track.updated_at,
        }

    async def get_active_caption_track(
        self,
        db: AsyncSession,
        project_id: uuid.UUID
    ) -> Optional[Dict[str, Any]]:
        """Fetches currently active caption track for a project."""
        res = await db.execute(
            select(CaptionTrack.id).where(
                CaptionTrack.project_id == project_id,
                CaptionTrack.is_active == True
            )
        )
        active_id = res.scalar_one_or_none()
        if not active_id:
            return None
        return await self.get_caption_track(db, active_id)

    async def get_caption_track_versions(
        self,
        db: AsyncSession,
        project_id: uuid.UUID
    ) -> List[Dict[str, Any]]:
        """Returns summaries of all caption tracks for a project."""
        res = await db.execute(
            select(CaptionTrack)
            .where(CaptionTrack.project_id == project_id)
            .order_by(CaptionTrack.version.desc())
        )
        tracks = res.scalars().all()
        results = []
        for t in tracks:
            results.append({
                "id": t.id,
                "project_id": t.project_id,
                "script_id": t.script_id,
                "tts_generation_id": t.tts_generation_id,
                "production_timeline_id": t.production_timeline_id,
                "version": t.version,
                "language": t.language,
                "status": t.status.value if hasattr(t.status, "value") else str(t.status),
                "total_duration": t.total_duration,
                "total_segments": t.total_segments,
                "is_active": t.is_active,
                "is_stale": False,
                "created_at": t.created_at,
                "updated_at": t.updated_at,
            })
        return results

    async def activate_caption_track(
        self,
        db: AsyncSession,
        track_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Sets target caption track as active and deactivates others."""
        res = await db.execute(select(CaptionTrack).where(CaptionTrack.id == track_id))
        track = res.scalar_one_or_none()
        if not track:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caption track not found.")

        await db.execute(
            update(CaptionTrack)
            .where(CaptionTrack.project_id == track.project_id)
            .values(is_active=False)
        )

        track.is_active = True
        await db.commit()
        await db.refresh(track)

        return await self.get_caption_track(db, track.id)

    async def update_caption_segment(
        self,
        db: AsyncSession,
        segment_id: uuid.UUID,
        text: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        style: Optional[str] = None,
        position: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Updates an individual caption segment. Validates bounds against parent audio segment.
        """
        query = (
            select(CaptionSegment)
            .options(
                joinedload(CaptionSegment.audio_segment),
                joinedload(CaptionSegment.track)
            )
            .where(CaptionSegment.id == segment_id)
        )
        res = await db.execute(query)
        segment = res.scalar_one_or_none()
        if not segment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caption segment not found.")

        # Validate & update text
        if text is not None:
            if not text.strip():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Caption text cannot be empty.")
            segment.text = text.strip()

        # Validate & update timings
        new_start = start_time if start_time is not None else segment.start_time
        new_end = end_time if end_time is not None else segment.end_time

        if start_time is not None or end_time is not None:
            if new_start < 0:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Start time cannot be negative.")
            if new_end <= new_start:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="End time must be strictly greater than start time."
                )

            # Validate against parent audio segment boundaries if present
            audio_seg = segment.audio_segment
            if audio_seg:
                if new_start < audio_seg.start_time - 0.1:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Caption start time ({new_start:.2f}s) cannot precede audio segment start ({audio_seg.start_time:.2f}s)."
                    )
                if new_end > audio_seg.end_time + 0.1:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Caption end time ({new_end:.2f}s) cannot exceed audio segment end ({audio_seg.end_time:.2f}s)."
                    )

            segment.start_time = round(new_start, 2)
            segment.end_time = round(new_end, 2)
            segment.duration = round(new_end - new_start, 2)

        # Style & Position
        if style is not None:
            valid_styles = {"default", "bold", "highlight"}
            if style.lower() not in valid_styles:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid style '{style}'. Supported values: {valid_styles}"
                )
            segment.style = style.lower()

        if position is not None:
            valid_positions = {"top", "center", "bottom"}
            if position.lower() not in valid_positions:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid position '{position}'. Supported values: {valid_positions}"
                )
            segment.position = position.lower()

        await db.commit()
        await db.refresh(segment)

        return await self.get_caption_track(db, segment.caption_track_id)

    async def export_srt(
        self,
        db: AsyncSession,
        track_id: uuid.UUID
    ) -> str:
        """
        Exports caption track in standard SubRip SRT format:
        1
        00:00:00,000 --> 00:00:01,200
        Caption text
        """
        query = (
            select(CaptionSegment)
            .where(CaptionSegment.caption_track_id == track_id)
            .order_by(CaptionSegment.sequence.asc())
        )
        res = await db.execute(query)
        segments = res.scalars().all()
        if not segments:
            return ""

        srt_blocks: List[str] = []
        for idx, seg in enumerate(segments, start=1):
            start_str = format_srt_timestamp(seg.start_time)
            end_str = format_srt_timestamp(seg.end_time)
            text_str = seg.text.strip()
            srt_blocks.append(f"{idx}\n{start_str} --> {end_str}\n{text_str}\n")

        return "\n".join(srt_blocks)


caption_generation_service = CaptionGenerationService()

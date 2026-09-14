import uuid
import logging
from typing import List, Dict, Any, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import select, func, update
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.models.scene import Scene
from app.models.keyframe import Keyframe
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

logger = logging.getLogger("shorts_api.timeline.service")


class ProductionTimelineService:
    """
    Orchestration service for generating, versioning, and managing
    the unified production timeline / shot plan (Milestone 7).
    """

    async def generate_timeline(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        script_id: Optional[uuid.UUID] = None,
        tts_generation_id: Optional[uuid.UUID] = None,
    ) -> ProductionTimeline:
        """
        Builds a deterministic production timeline combining:
        1. Reference Scenes (M3)
        2. Indonesian Script Segments (M4)
        3. TTS Narration Audio Segments (M5) -> PRIMARY TIMING SOURCE
        4. Selected Footage Candidates (M6)
        """
        # 1. Verify project exists
        proj_res = await db.execute(select(Project).where(Project.id == project_id))
        project = proj_res.scalar_one_or_none()
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")

        # 2. Resolve Script
        if script_id:
            script_res = await db.execute(
                select(Script).where(Script.id == script_id, Script.project_id == project_id)
            )
            script = script_res.scalar_one_or_none()
            if not script or script.status != ScriptStatus.READY:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Specified script was not found or is not in 'ready' status."
                )
        else:
            script_res = await db.execute(
                select(Script).where(
                    Script.project_id == project_id,
                    Script.is_active == True,
                    Script.status == ScriptStatus.READY
                )
            )
            script = script_res.scalar_one_or_none()
            if not script:
                # Try latest ready script if is_active is not set
                script_res = await db.execute(
                    select(Script).where(
                        Script.project_id == project_id,
                        Script.status == ScriptStatus.READY
                    ).order_by(Script.version.desc())
                )
                script = script_res.scalars().first()
                if not script:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="No ready Indonesian script found for this project. Complete Milestone 4 first."
                    )

        # 3. Resolve TTS Generation
        if tts_generation_id:
            tts_res = await db.execute(
                select(TTSGeneration).where(
                    TTSGeneration.id == tts_generation_id,
                    TTSGeneration.project_id == project_id
                )
            )
            tts_gen = tts_res.scalar_one_or_none()
            if not tts_gen or tts_gen.status != TTSStatus.COMPLETED:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Specified TTS generation was not found or is not 'completed'."
                )
        else:
            tts_res = await db.execute(
                select(TTSGeneration).where(
                    TTSGeneration.project_id == project_id,
                    TTSGeneration.is_active == True,
                    TTSGeneration.status == TTSStatus.COMPLETED
                )
            )
            tts_gen = tts_res.scalar_one_or_none()
            if not tts_gen:
                # Try latest completed TTS generation
                tts_res = await db.execute(
                    select(TTSGeneration).where(
                        TTSGeneration.project_id == project_id,
                        TTSGeneration.status == TTSStatus.COMPLETED
                    ).order_by(TTSGeneration.created_at.desc())
                )
                tts_gen = tts_res.scalars().first()
                if not tts_gen:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="No completed TTS narration audio found for this project. Complete Milestone 5 first."
                    )

        # 4. Fetch Scenes ordered by sequence
        scenes_res = await db.execute(
            select(Scene).where(Scene.project_id == project_id).order_by(Scene.sequence.asc())
        )
        scenes = list(scenes_res.scalars().all())
        if not scenes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project has no reference scenes. Run reference video analysis (Milestone 3) first."
            )

        # 5. Fetch Audio Segments for this TTS Generation
        audio_segs_res = await db.execute(
            select(AudioSegment).where(
                AudioSegment.tts_generation_id == tts_gen.id
            ).order_by(AudioSegment.sequence.asc())
        )
        audio_segs = list(audio_segs_res.scalars().all())

        # Map audio segments by scene_id (string) and by sequence
        audio_seg_by_scene_id: Dict[str, AudioSegment] = {}
        audio_seg_by_seq: Dict[int, AudioSegment] = {}
        for aseg in audio_segs:
            if aseg.scene_id:
                audio_seg_by_scene_id[str(aseg.scene_id)] = aseg
            audio_seg_by_seq[aseg.sequence] = aseg

        # Map script segments by scene_id and sequence
        script_segs = script.segments or []
        script_seg_by_scene_id: Dict[str, Dict[str, Any]] = {}
        script_seg_by_seq: Dict[int, Dict[str, Any]] = {}
        for sseg in script_segs:
            if isinstance(sseg, dict):
                sid = sseg.get("scene_id")
                if sid:
                    script_seg_by_scene_id[str(sid)] = sseg
                seq = sseg.get("sequence")
                if isinstance(seq, int):
                    script_seg_by_seq[seq] = sseg

        # 6. Fetch Selected Footage for each scene
        scene_ids = [s.id for s in scenes]
        selections_res = await db.execute(
            select(SceneFootageSelection)
            .options(joinedload(SceneFootageSelection.candidate))
            .where(SceneFootageSelection.scene_id.in_(scene_ids))
        )
        selections = list(selections_res.scalars().all())
        selection_by_scene_id: Dict[uuid.UUID, SceneFootageSelection] = {
            sel.scene_id: sel for sel in selections
        }

        # 7. Calculate Next Version Number for project
        ver_res = await db.execute(
            select(func.max(ProductionTimeline.version)).where(ProductionTimeline.project_id == project_id)
        )
        current_max_ver = ver_res.scalar() or 0
        new_version = current_max_ver + 1

        # 8. Build Timeline Items
        timeline_items: List[ProductionTimelineItem] = []
        scenes_with_footage = 0
        scenes_missing_footage = 0
        cumulative_time = 0.0
        prev_footage_candidate_id: Optional[uuid.UUID] = None
        prev_footage_end_time: float = 0.0

        for scene in scenes:
            scene_str_id = str(scene.id)

            # Match Audio Segment (PRIMARY TIMING SOURCE)
            audio_seg = audio_seg_by_scene_id.get(scene_str_id) or audio_seg_by_seq.get(scene.sequence)
            script_seg = script_seg_by_scene_id.get(scene_str_id) or script_seg_by_seq.get(scene.sequence)

            if audio_seg:
                start_time = round(audio_seg.start_time, 2)
                end_time = round(audio_seg.end_time, 2)
                duration = round(audio_seg.duration, 2)
                script_text = audio_seg.text or (script_seg.get("adapted_text", "") if script_seg else "")
                audio_segment_id = audio_seg.id
            else:
                # Fallback if audio segment missing for this scene
                start_time = round(cumulative_time, 2)
                est_dur = float(script_seg.get("estimated_duration", 0.0) if script_seg else 0.0)
                dur = est_dur if est_dur > 0.5 else (scene.duration or 3.0)
                duration = round(dur, 2)
                end_time = round(start_time + duration, 2)
                script_text = script_seg.get("adapted_text", "") if script_seg else ""
                audio_segment_id = None

            cumulative_time = max(cumulative_time, end_time)

            # Match Footage Selection
            selection = selection_by_scene_id.get(scene.id)
            candidate: Optional[FootageCandidate] = selection.candidate if selection else None

            if candidate:
                scenes_with_footage += 1
                footage_candidate_id = candidate.id
                footage_source_url = candidate.source_url

                # Continuous trimming: continue from previous scene if same candidate
                if prev_footage_candidate_id and prev_footage_candidate_id == candidate.id:
                    footage_start_time = round(prev_footage_end_time, 2)
                else:
                    footage_start_time = 0.0

                footage_end_time = round(footage_start_time + duration, 2)

                # Handle Footage Duration Logic (Section 7)
                cand_dur = candidate.duration
                if cand_dur is not None and cand_dur > 0:
                    duration_unknown = False
                    if cand_dur >= footage_end_time:
                        insufficient_footage_duration = False
                    else:
                        # Shorter than required continuous segment
                        insufficient_footage_duration = True
                else:
                    # Duration unknown
                    duration_unknown = True
                    insufficient_footage_duration = False

                prev_footage_candidate_id = candidate.id
                prev_footage_end_time = footage_end_time
            else:
                # Missing footage
                scenes_missing_footage += 1
                footage_candidate_id = None
                footage_source_url = None
                footage_start_time = 0.0
                footage_end_time = 0.0
                insufficient_footage_duration = False
                duration_unknown = False
                prev_footage_candidate_id = None
                prev_footage_end_time = 0.0

            item = ProductionTimelineItem(
                scene_id=scene.id,
                sequence=scene.sequence,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                script_text=script_text,
                audio_segment_id=audio_segment_id,
                footage_candidate_id=footage_candidate_id,
                footage_source_url=footage_source_url,
                footage_start_time=footage_start_time,
                footage_end_time=footage_end_time,
                transition="cut",
                insufficient_footage_duration=insufficient_footage_duration,
                duration_unknown=duration_unknown,
                notes=selection.notes if selection else None,
            )
            timeline_items.append(item)

        # 9. Deactivate previous timelines
        await db.execute(
            update(ProductionTimeline)
            .where(ProductionTimeline.project_id == project_id)
            .values(is_active=False)
        )

        # 10. Create Production Timeline Record
        total_duration = round(cumulative_time, 2)
        timeline = ProductionTimeline(
            project_id=project_id,
            script_id=script.id,
            tts_generation_id=tts_gen.id,
            version=new_version,
            status=TimelineStatus.READY,
            duration=total_duration,
            total_scenes=len(scenes),
            scenes_with_footage=scenes_with_footage,
            scenes_missing_footage=scenes_missing_footage,
            is_active=True,
            items=timeline_items,
        )

        db.add(timeline)
        await db.commit()
        await db.refresh(timeline)

        logger.info(
            f"Created Production Timeline v{new_version} for project {project_id} "
            f"({len(timeline_items)} items, duration {total_duration}s, {scenes_with_footage}/{len(scenes)} footage coverage)"
        )
        return await self.get_timeline(db, timeline.id)

    async def check_stale_status(
        self,
        db: AsyncSession,
        timeline: ProductionTimeline
    ) -> Tuple[bool, List[str]]:
        """
        Detects whether this timeline has become outdated due to:
        - Active script changes
        - Active TTS changes
        - Scene footage selection updates
        """
        reasons: List[str] = []

        # 1. Check active script
        active_script_res = await db.execute(
            select(Script.id).where(
                Script.project_id == timeline.project_id,
                Script.is_active == True,
                Script.status == ScriptStatus.READY
            )
        )
        active_script_id = active_script_res.scalar_one_or_none()
        if active_script_id and active_script_id != timeline.script_id:
            reasons.append("Active Indonesian script has changed since this timeline was generated.")

        # 2. Check active TTS generation
        active_tts_res = await db.execute(
            select(TTSGeneration.id).where(
                TTSGeneration.project_id == timeline.project_id,
                TTSGeneration.is_active == True,
                TTSGeneration.status == TTSStatus.COMPLETED
            )
        )
        active_tts_id = active_tts_res.scalar_one_or_none()
        if active_tts_id and active_tts_id != timeline.tts_generation_id:
            reasons.append("Active TTS narration audio has changed since this timeline was generated.")

        # 3. Check footage selections
        if timeline.items:
            scene_ids = [item.scene_id for item in timeline.items]
            selections_res = await db.execute(
                select(SceneFootageSelection).where(SceneFootageSelection.scene_id.in_(scene_ids))
            )
            current_selections = {sel.scene_id: sel.candidate_id for sel in selections_res.scalars().all()}

            selection_differs = False
            for item in timeline.items:
                current_cand_id = current_selections.get(item.scene_id)
                if item.footage_candidate_id != current_cand_id:
                    selection_differs = True
                    break

            if selection_differs:
                reasons.append("Footage candidate selections for one or more scenes have changed.")

        is_stale = len(reasons) > 0
        return is_stale, reasons

    async def get_timeline(
        self,
        db: AsyncSession,
        timeline_id: uuid.UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Fetches full details of a specific timeline including items, scene keyframes,
        candidate details, stale status, and average similarity score.
        """
        query = (
            select(ProductionTimeline)
            .options(
                selectinload(ProductionTimeline.items)
                .joinedload(ProductionTimelineItem.scene)
                .selectinload(Scene.keyframes),
                selectinload(ProductionTimeline.items)
                .joinedload(ProductionTimelineItem.footage_candidate),
            )
            .where(ProductionTimeline.id == timeline_id)
        )
        res = await db.execute(query)
        timeline = res.scalar_one_or_none()
        if not timeline:
            return None

        is_stale, stale_reasons = await self.check_stale_status(db, timeline)

        # Prepare formatted items with nested brief objects
        formatted_items = []
        similarities = []

        for item in timeline.items:
            scene = item.scene
            cand = item.footage_candidate

            # Primary keyframe for reference scene
            pk_url = None
            if scene and scene.keyframes:
                primary = next((k for k in scene.keyframes if k.is_primary), scene.keyframes[0])
                pk_url = primary.image_path

            scene_brief = None
            if scene:
                scene_brief = {
                    "id": scene.id,
                    "sequence": scene.sequence,
                    "start_time": scene.start_time,
                    "end_time": scene.end_time,
                    "visual_description": scene.visual_description,
                    "primary_keyframe_url": pk_url,
                }

            cand_brief = None
            if cand:
                cand_brief = {
                    "id": cand.id,
                    "title": cand.title,
                    "source_platform": cand.source_platform,
                    "source_url": cand.source_url,
                    "thumbnail_url": cand.thumbnail_url,
                    "duration": cand.duration,
                    "visual_score": cand.visual_score,
                    "context_score": cand.context_score,
                    "final_score": cand.final_score,
                    "match_type": cand.match_type,
                }
                similarities.append(cand.final_score)

            formatted_items.append({
                "id": item.id,
                "timeline_id": item.timeline_id,
                "scene_id": item.scene_id,
                "sequence": item.sequence,
                "start_time": item.start_time,
                "end_time": item.end_time,
                "duration": item.duration,
                "script_text": item.script_text,
                "audio_segment_id": item.audio_segment_id,
                "footage_candidate_id": item.footage_candidate_id,
                "footage_source_url": item.footage_source_url,
                "footage_start_time": item.footage_start_time,
                "footage_end_time": item.footage_end_time,
                "transition": item.transition,
                "insufficient_footage_duration": item.insufficient_footage_duration,
                "duration_unknown": item.duration_unknown,
                "notes": item.notes,
                "scene": scene_brief,
                "candidate": cand_brief,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
            })

        avg_similarity = round(sum(similarities) / len(similarities), 4) if similarities else None

        return {
            "id": timeline.id,
            "project_id": timeline.project_id,
            "script_id": timeline.script_id,
            "tts_generation_id": timeline.tts_generation_id,
            "version": timeline.version,
            "status": timeline.status.value if hasattr(timeline.status, "value") else str(timeline.status),
            "duration": timeline.duration,
            "total_scenes": timeline.total_scenes,
            "scenes_with_footage": timeline.scenes_with_footage,
            "scenes_missing_footage": timeline.scenes_missing_footage,
            "is_active": timeline.is_active,
            "is_stale": is_stale,
            "stale_reasons": stale_reasons,
            "average_similarity": avg_similarity,
            "items": formatted_items,
            "created_at": timeline.created_at,
            "updated_at": timeline.updated_at,
        }

    async def get_active_timeline(
        self,
        db: AsyncSession,
        project_id: uuid.UUID
    ) -> Optional[Dict[str, Any]]:
        """Fetches the current active timeline for a project."""
        active_res = await db.execute(
            select(ProductionTimeline.id).where(
                ProductionTimeline.project_id == project_id,
                ProductionTimeline.is_active == True
            )
        )
        active_id = active_res.scalar_one_or_none()
        if not active_id:
            return None
        return await self.get_timeline(db, active_id)

    async def get_timeline_versions(
        self,
        db: AsyncSession,
        project_id: uuid.UUID
    ) -> List[Dict[str, Any]]:
        """Returns summary list of all timeline versions for a project."""
        res = await db.execute(
            select(ProductionTimeline)
            .where(ProductionTimeline.project_id == project_id)
            .order_by(ProductionTimeline.version.desc())
        )
        timelines = res.scalars().all()
        results = []
        for t in timelines:
            results.append({
                "id": t.id,
                "project_id": t.project_id,
                "script_id": t.script_id,
                "tts_generation_id": t.tts_generation_id,
                "version": t.version,
                "status": t.status.value if hasattr(t.status, "value") else str(t.status),
                "duration": t.duration,
                "total_scenes": t.total_scenes,
                "scenes_with_footage": t.scenes_with_footage,
                "scenes_missing_footage": t.scenes_missing_footage,
                "is_active": t.is_active,
                "is_stale": False,
                "created_at": t.created_at,
                "updated_at": t.updated_at,
            })
        return results

    async def activate_timeline(
        self,
        db: AsyncSession,
        timeline_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Sets target timeline as active and deactivates other versions."""
        res = await db.execute(select(ProductionTimeline).where(ProductionTimeline.id == timeline_id))
        timeline = res.scalar_one_or_none()
        if not timeline:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timeline not found.")

        # Deactivate all timelines for this project
        await db.execute(
            update(ProductionTimeline)
            .where(ProductionTimeline.project_id == timeline.project_id)
            .values(is_active=False)
        )

        timeline.is_active = True
        await db.commit()
        await db.refresh(timeline)

        return await self.get_timeline(db, timeline.id)

    async def update_timeline_item(
        self,
        db: AsyncSession,
        item_id: uuid.UUID,
        footage_candidate_id: Optional[uuid.UUID] = None,
        footage_start_time: Optional[float] = None,
        footage_end_time: Optional[float] = None,
        transition: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Updates an individual timeline item (footage assignment, manual trim, transition, notes).
        Narration audio timing is protected and immutable from this endpoint.
        """
        query = (
            select(ProductionTimelineItem)
            .options(
                joinedload(ProductionTimelineItem.timeline),
                joinedload(ProductionTimelineItem.footage_candidate),
            )
            .where(ProductionTimelineItem.id == item_id)
        )
        res = await db.execute(query)
        item = res.scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timeline item not found.")

        timeline = item.timeline

        # 1. Update footage candidate if requested
        if footage_candidate_id is not None:
            cand_res = await db.execute(
                select(FootageCandidate).where(FootageCandidate.id == footage_candidate_id)
            )
            candidate = cand_res.scalar_one_or_none()
            if not candidate:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate footage not found.")

            item.footage_candidate_id = candidate.id
            item.footage_source_url = candidate.source_url
            item.footage_candidate = candidate

            # Default trim values for new candidate
            if candidate.duration is not None and candidate.duration > 0:
                item.duration_unknown = False
                if candidate.duration >= item.duration:
                    item.footage_start_time = 0.0
                    item.footage_end_time = item.duration
                    item.insufficient_footage_duration = False
                else:
                    item.footage_start_time = 0.0
                    item.footage_end_time = round(candidate.duration, 2)
                    item.insufficient_footage_duration = True
            else:
                item.duration_unknown = True
                item.insufficient_footage_duration = False
                item.footage_start_time = 0.0
                item.footage_end_time = item.duration

        # 2. Update and validate manual trim timings
        new_start = footage_start_time if footage_start_time is not None else item.footage_start_time
        new_end = footage_end_time if footage_end_time is not None else item.footage_end_time

        if footage_start_time is not None or footage_end_time is not None:
            if new_start < 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Footage start time cannot be negative."
                )
            if new_end <= new_start:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Footage end time must be strictly greater than start time."
                )

            # Check candidate bounds if duration known
            cand = item.footage_candidate
            if cand and cand.duration is not None and cand.duration > 0:
                if new_end > cand.duration + 0.1:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Footage end time ({new_end:.2f}s) exceeds source video duration ({cand.duration:.2f}s)."
                    )

            item.footage_start_time = round(new_start, 2)
            item.footage_end_time = round(new_end, 2)

        # 3. Update transition
        if transition is not None:
            valid_transitions = {"cut", "fade"}
            if transition.lower() not in valid_transitions:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid transition '{transition}'. Supported values: {valid_transitions}"
                )
            item.transition = transition.lower()

        # 4. Update notes
        if notes is not None:
            item.notes = notes

        # 5. Recompute timeline footage counts
        items_res = await db.execute(
            select(ProductionTimelineItem).where(ProductionTimelineItem.timeline_id == timeline.id)
        )
        all_items = items_res.scalars().all()
        with_footage = sum(1 for it in all_items if it.footage_candidate_id is not None)
        missing_footage = len(all_items) - with_footage

        timeline.scenes_with_footage = with_footage
        timeline.scenes_missing_footage = missing_footage

        await db.commit()
        await db.refresh(item)

        # Return updated timeline
        return await self.get_timeline(db, timeline.id)


production_timeline_service = ProductionTimelineService()

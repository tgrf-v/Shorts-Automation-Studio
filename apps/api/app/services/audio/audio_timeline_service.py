import uuid
import logging
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_
from sqlalchemy.orm import selectinload

from app.models.audio_mix import AudioTimeline, AudioLayer, AudioAsset, AudioType, AudioTimelineStatus
from app.models.production_timeline import ProductionTimeline, ProductionTimelineItem
from app.models.tts_generation import TTSGeneration, TTSStatus
from app.models.audio_segment import AudioSegment

logger = logging.getLogger("shorts_api.services.audio.timeline")


class AudioTimelineService:
    """
    Service managing BGM & SFX audio timeline configuration, layering,
    validation, versioning, and stale state detection.
    """

    @staticmethod
    def validate_layer_timing(
        start_time: float,
        end_time: float,
        volume: float,
        fade_in: float,
        fade_out: float,
        max_duration: Optional[float] = None
    ) -> None:
        """Validates layer timestamps, volume, and fades."""
        if start_time < 0:
            raise ValueError(f"start_time ({start_time}s) cannot be negative.")
        if end_time <= start_time:
            raise ValueError(f"end_time ({end_time}s) must be strictly greater than start_time ({start_time}s).")
        if volume < -60.0 or volume > 12.0:
            raise ValueError(f"volume ({volume} dB) must be within [-60.0 dB, +12.0 dB].")
        if fade_in < 0:
            raise ValueError(f"fade_in ({fade_in}s) cannot be negative.")
        if fade_out < 0:
            raise ValueError(f"fade_out ({fade_out}s) cannot be negative.")
        if max_duration is not None and max_duration > 0:
            # Allow up to 10 seconds leeway beyond timeline for ambient trails/tails
            if start_time > max_duration + 5.0:
                raise ValueError(f"start_time ({start_time}s) exceeds timeline duration ({max_duration}s).")

    @classmethod
    async def generate_audio_timeline(
        cls,
        db: AsyncSession,
        project_id: uuid.UUID,
        bgm_asset_id: Optional[uuid.UUID] = None,
        production_timeline_id: Optional[uuid.UUID] = None,
        ducking_enabled: bool = True,
        ducking_level: float = -6.0
    ) -> AudioTimeline:
        """
        Generates a new AudioTimeline version linking the active production timeline
        and TTS narration, with optional initial BGM layer.
        """
        # 1. Resolve Production Timeline
        if production_timeline_id:
            pt_res = await db.execute(
                select(ProductionTimeline).where(ProductionTimeline.id == production_timeline_id)
            )
            prod_timeline = pt_res.scalar_one_or_none()
        else:
            pt_res = await db.execute(
                select(ProductionTimeline).where(
                    and_(
                        ProductionTimeline.project_id == project_id,
                        ProductionTimeline.is_active == True
                    )
                )
            )
            prod_timeline = pt_res.scalar_one_or_none()

        if not prod_timeline:
            raise ValueError(
                f"No active Production Timeline found for project {project_id}. "
                "Generate a production timeline (Milestone 7) first."
            )

        total_duration = prod_timeline.total_duration

        # 2. Determine next version number
        ver_res = await db.execute(
            select(func.max(AudioTimeline.version)).where(AudioTimeline.project_id == project_id)
        )
        max_v = ver_res.scalar() or 0
        new_version = max_v + 1

        # 3. Deactivate existing active audio timelines for this project
        await db.execute(
            update(AudioTimeline)
            .where(and_(AudioTimeline.project_id == project_id, AudioTimeline.is_active == True))
            .values(is_active=False)
        )

        # 4. Create new AudioTimeline container
        timeline = AudioTimeline(
            project_id=project_id,
            production_timeline_id=prod_timeline.id,
            version=new_version,
            status=AudioTimelineStatus.READY,
            total_duration=total_duration,
            is_active=True,
            ducking_enabled=ducking_enabled,
            ducking_level=ducking_level
        )
        db.add(timeline)
        await db.flush()

        # 5. Add initial BGM layer if requested
        if bgm_asset_id:
            asset_res = await db.execute(select(AudioAsset).where(AudioAsset.id == bgm_asset_id))
            bgm_asset = asset_res.scalar_one_or_none()
            if bgm_asset:
                bgm_layer = AudioLayer(
                    project_id=project_id,
                    audio_timeline_id=timeline.id,
                    audio_asset_id=bgm_asset.id,
                    type=AudioType.BGM,
                    name=bgm_asset.name,
                    start_time=0.0,
                    end_time=round(total_duration, 2),
                    volume=-18.0,
                    fade_in=1.0,
                    fade_out=2.0,
                    loop=True,
                    enabled=True,
                    ducking_enabled=True,
                    ducking_level=ducking_level,
                    notes="Auto-assigned background music bed"
                )
                db.add(bgm_layer)

        await db.commit()
        await db.refresh(timeline)
        return timeline

    @classmethod
    async def get_active_timeline(
        cls,
        db: AsyncSession,
        project_id: uuid.UUID
    ) -> Tuple[Optional[AudioTimeline], bool, List[str]]:
        """
        Retrieves active AudioTimeline for a project along with stale state detection.
        Returns: (AudioTimeline, is_stale, stale_reasons)
        """
        res = await db.execute(
            select(AudioTimeline)
            .where(and_(AudioTimeline.project_id == project_id, AudioTimeline.is_active == True))
            .options(
                selectinload(AudioTimeline.layers).selectinload(AudioLayer.audio_asset),
                selectinload(AudioTimeline.production_timeline)
            )
        )
        timeline = res.scalar_one_or_none()
        if not timeline:
            return None, False, []

        is_stale = False
        stale_reasons: List[str] = []

        # Check if active production timeline has changed
        active_pt_res = await db.execute(
            select(ProductionTimeline).where(
                and_(ProductionTimeline.project_id == project_id, ProductionTimeline.is_active == True)
            )
        )
        active_pt = active_pt_res.scalar_one_or_none()

        if not active_pt:
            is_stale = True
            stale_reasons.append("Active production timeline is missing or removed.")
        elif active_pt.id != timeline.production_timeline_id:
            is_stale = True
            stale_reasons.append(
                f"Active production timeline was updated to v{active_pt.version} "
                f"(Audio timeline was built against v{timeline.production_timeline.version if timeline.production_timeline else '?'})."
            )
        elif abs(active_pt.total_duration - timeline.total_duration) > 0.5:
            is_stale = True
            stale_reasons.append(
                f"Timeline duration changed from {timeline.total_duration:.2f}s to {active_pt.total_duration:.2f}s."
            )

        return timeline, is_stale, stale_reasons

    @classmethod
    async def list_versions(
        cls,
        db: AsyncSession,
        project_id: uuid.UUID
    ) -> List[AudioTimeline]:
        """Lists historical audio timeline versions for project."""
        res = await db.execute(
            select(AudioTimeline)
            .where(AudioTimeline.project_id == project_id)
            .order_by(AudioTimeline.version.desc())
            .options(selectinload(AudioTimeline.layers))
        )
        return list(res.scalars().all())

    @classmethod
    async def get_timeline_by_id(
        cls,
        db: AsyncSession,
        timeline_id: uuid.UUID
    ) -> Optional[AudioTimeline]:
        """Retrieves an AudioTimeline by ID with layers and assets."""
        res = await db.execute(
            select(AudioTimeline)
            .where(AudioTimeline.id == timeline_id)
            .options(
                selectinload(AudioTimeline.layers).selectinload(AudioLayer.audio_asset),
                selectinload(AudioTimeline.production_timeline)
            )
        )
        return res.scalar_one_or_none()

    @classmethod
    async def activate_timeline(
        cls,
        db: AsyncSession,
        timeline_id: uuid.UUID
    ) -> AudioTimeline:
        """Sets a specific audio timeline version as active."""
        timeline = await cls.get_timeline_by_id(db, timeline_id)
        if not timeline:
            raise ValueError(f"Audio timeline {timeline_id} not found.")

        await db.execute(
            update(AudioTimeline)
            .where(and_(AudioTimeline.project_id == timeline.project_id, AudioTimeline.is_active == True))
            .values(is_active=False)
        )
        timeline.is_active = True
        await db.commit()
        await db.refresh(timeline)
        return timeline

    @classmethod
    async def add_layer(
        cls,
        db: AsyncSession,
        project_id: uuid.UUID,
        audio_timeline_id: uuid.UUID,
        audio_asset_id: uuid.UUID,
        layer_type: AudioType,
        name: Optional[str] = None,
        start_time: float = 0.0,
        end_time: Optional[float] = None,
        volume: Optional[float] = None,
        fade_in: float = 0.0,
        fade_out: float = 0.0,
        loop: Optional[bool] = None,
        enabled: bool = True,
        ducking_enabled: Optional[bool] = None,
        ducking_level: float = -6.0,
        scene_id: Optional[uuid.UUID] = None,
        notes: Optional[str] = None
    ) -> AudioLayer:
        """Adds a BGM or SFX layer to an audio timeline."""
        timeline = await cls.get_timeline_by_id(db, audio_timeline_id)
        if not timeline:
            raise ValueError(f"Audio timeline {audio_timeline_id} not found.")

        asset_res = await db.execute(select(AudioAsset).where(AudioAsset.id == audio_asset_id))
        asset = asset_res.scalar_one_or_none()
        if not asset:
            raise ValueError(f"Audio asset {audio_asset_id} not found.")

        # Resolve end_time: if not given, use asset duration or timeline duration
        if end_time is None:
            if layer_type == AudioType.BGM:
                end_time = round(timeline.total_duration, 2)
            else:
                asset_dur = asset.duration if asset.duration > 0 else 1.0
                end_time = round(start_time + asset_dur, 2)

        # Defaults based on layer type
        if volume is None:
            volume = -18.0 if layer_type == AudioType.BGM else -6.0
        if loop is None:
            loop = True if layer_type == AudioType.BGM else False
        if ducking_enabled is None:
            ducking_enabled = True if layer_type == AudioType.BGM else False

        cls.validate_layer_timing(
            start_time=start_time,
            end_time=end_time,
            volume=volume,
            fade_in=fade_in,
            fade_out=fade_out,
            max_duration=timeline.total_duration
        )

        display_name = name or asset.name

        layer = AudioLayer(
            project_id=project_id,
            audio_timeline_id=audio_timeline_id,
            audio_asset_id=audio_asset_id,
            scene_id=scene_id,
            type=layer_type,
            name=display_name,
            start_time=round(start_time, 2),
            end_time=round(end_time, 2),
            volume=round(volume, 2),
            fade_in=round(fade_in, 2),
            fade_out=round(fade_out, 2),
            loop=loop,
            enabled=enabled,
            ducking_enabled=ducking_enabled,
            ducking_level=round(ducking_level, 2),
            notes=notes
        )
        db.add(layer)
        await db.commit()
        await db.refresh(layer)
        return layer

    @classmethod
    async def update_layer(
        cls,
        db: AsyncSession,
        layer_id: uuid.UUID,
        name: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        volume: Optional[float] = None,
        fade_in: Optional[float] = None,
        fade_out: Optional[float] = None,
        loop: Optional[bool] = None,
        enabled: Optional[bool] = None,
        ducking_enabled: Optional[bool] = None,
        ducking_level: Optional[float] = None,
        notes: Optional[str] = None
    ) -> AudioLayer:
        """Updates properties of an existing audio layer."""
        res = await db.execute(
            select(AudioLayer)
            .where(AudioLayer.id == layer_id)
            .options(selectinload(AudioLayer.audio_timeline))
        )
        layer = res.scalar_one_or_none()
        if not layer:
            raise ValueError(f"Audio layer {layer_id} not found.")

        target_start = start_time if start_time is not None else layer.start_time
        target_end = end_time if end_time is not None else layer.end_time
        target_vol = volume if volume is not None else layer.volume
        target_fade_in = fade_in if fade_in is not None else layer.fade_in
        target_fade_out = fade_out if fade_out is not None else layer.fade_out

        max_dur = layer.audio_timeline.total_duration if layer.audio_timeline else None

        cls.validate_layer_timing(
            start_time=target_start,
            end_time=target_end,
            volume=target_vol,
            fade_in=target_fade_in,
            fade_out=target_fade_out,
            max_duration=max_dur
        )

        if name is not None:
            layer.name = name
        layer.start_time = round(target_start, 2)
        layer.end_time = round(target_end, 2)
        layer.volume = round(target_vol, 2)
        layer.fade_in = round(target_fade_in, 2)
        layer.fade_out = round(target_fade_out, 2)
        if loop is not None:
            layer.loop = loop
        if enabled is not None:
            layer.enabled = enabled
        if ducking_enabled is not None:
            layer.ducking_enabled = ducking_enabled
        if ducking_level is not None:
            layer.ducking_level = round(ducking_level, 2)
        if notes is not None:
            layer.notes = notes

        await db.commit()
        await db.refresh(layer)
        return layer

    @classmethod
    async def delete_layer(
        cls,
        db: AsyncSession,
        layer_id: uuid.UUID
    ) -> bool:
        """Deletes an audio layer from timeline."""
        res = await db.execute(select(AudioLayer).where(AudioLayer.id == layer_id))
        layer = res.scalar_one_or_none()
        if not layer:
            return False

        await db.delete(layer)
        await db.commit()
        return True

    @classmethod
    async def get_renderer_mix_config(
        cls,
        db: AsyncSession,
        timeline_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Assembles renderer-ready structured audio mix configuration:
        - Priority 1: Narration (TTS segments)
        - Priority 2: SFX cues
        - Priority 3: BGM background bed
        """
        timeline = await cls.get_timeline_by_id(db, timeline_id)
        if not timeline:
            raise ValueError(f"Audio timeline {timeline_id} not found.")

        # Load narration audio segments from linked production timeline
        pt_res = await db.execute(
            select(ProductionTimelineItem)
            .where(ProductionTimelineItem.production_timeline_id == timeline.production_timeline_id)
            .order_by(ProductionTimelineItem.sequence.asc())
        )
        pt_items = pt_res.scalars().all()

        narration_tracks = []
        for item in pt_items:
            narration_tracks.append({
                "sequence": item.sequence,
                "start_time": item.start_time,
                "end_time": item.end_time,
                "duration": round(item.end_time - item.start_time, 2),
                "script_text": item.script_text,
                "audio_segment_id": str(item.audio_segment_id) if item.audio_segment_id else None,
                "volume_db": 0.0,  # Priority 1: Unity gain
                "priority": 1
            })

        sfx_layers = []
        bgm_layers = []

        for layer in timeline.layers:
            if not layer.enabled:
                continue
            layer_dict = {
                "id": str(layer.id),
                "name": layer.name,
                "type": layer.type.value if hasattr(layer.type, 'value') else str(layer.type),
                "start_time": layer.start_time,
                "end_time": layer.end_time,
                "duration": round(layer.end_time - layer.start_time, 2),
                "volume_db": layer.volume,
                "fade_in_sec": layer.fade_in,
                "fade_out_sec": layer.fade_out,
                "loop": layer.loop,
                "ducking_enabled": layer.ducking_enabled,
                "ducking_level_db": layer.ducking_level,
                "audio_asset": {
                    "id": str(layer.audio_asset.id),
                    "name": layer.audio_asset.name,
                    "file_path": layer.audio_asset.file_path,
                    "format": layer.audio_asset.format,
                    "duration": layer.audio_asset.duration
                } if layer.audio_asset else None
            }

            if layer.type == AudioType.SFX:
                layer_dict["priority"] = 2
                sfx_layers.append(layer_dict)
            else:
                layer_dict["priority"] = 3
                bgm_layers.append(layer_dict)

        return {
            "audio_timeline_id": str(timeline.id),
            "version": timeline.version,
            "total_duration": timeline.total_duration,
            "ducking_enabled": timeline.ducking_enabled,
            "ducking_level_db": timeline.ducking_level,
            "tracks": {
                "narration": narration_tracks,
                "sfx": sfx_layers,
                "bgm": bgm_layers
            }
        }

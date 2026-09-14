import os
import uuid
import logging
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_

from app.models.audio_mix import AudioAsset, AudioType
from app.services.audio.storage import BaseAudioStorage, LocalAudioStorage
from app.services.tts.audio_processor import AudioProcessorService

logger = logging.getLogger("shorts_api.services.audio.asset")


class AudioAssetService:
    """
    Manages BGM and SFX audio assets, technical metadata extraction via FFprobe,
    and storage.
    """

    def __init__(self, storage: Optional[BaseAudioStorage] = None):
        self.storage = storage or LocalAudioStorage()

    async def register_uploaded_asset(
        self,
        db: AsyncSession,
        content: bytes,
        filename: str,
        asset_type: AudioType,
        project_id: Optional[uuid.UUID] = None,
        name: Optional[str] = None,
        source_url: Optional[str] = None,
        custom_volume: Optional[float] = None
    ) -> AudioAsset:
        """
        Saves uploaded audio file, inspects audio metadata (duration, format, sample rate, channels),
        and records AudioAsset in the database.
        """
        display_name = name or os.path.splitext(filename)[0]
        file_path = await self.storage.save_file(content, project_id, filename)
        abs_path = self.storage.get_absolute_path(file_path)

        # Inspect metadata using AudioProcessorService (ffprobe + wave fallback)
        try:
            meta = await AudioProcessorService.inspect_audio(abs_path)
            duration = meta.duration
            format_name = meta.format_name or meta.codec or os.path.splitext(filename)[1].lstrip('.') or "mp3"
            sample_rate = meta.sample_rate
            channels = meta.channels
        except Exception as e:
            logger.warning(f"Failed to inspect audio with ffprobe for {filename}: {e}. Using defaults.")
            duration = 0.0
            format_name = os.path.splitext(filename)[1].lstrip('.') or "mp3"
            sample_rate = 44100
            channels = 2

        # Sensible native volume default: 0.0 dB
        vol = custom_volume if custom_volume is not None else 0.0

        asset = AudioAsset(
            project_id=project_id,
            type=asset_type,
            name=display_name,
            file_path=file_path,
            source_url=source_url,
            duration=duration,
            format=format_name,
            sample_rate=sample_rate,
            channels=channels,
            volume=vol
        )
        db.add(asset)
        await db.commit()
        await db.refresh(asset)
        return asset

    async def register_local_file_asset(
        self,
        db: AsyncSession,
        file_path: str,
        asset_type: AudioType,
        project_id: Optional[uuid.UUID] = None,
        name: Optional[str] = None,
        source_url: Optional[str] = None,
        custom_volume: Optional[float] = None
    ) -> AudioAsset:
        """
        Registers an existing local audio file as an AudioAsset.
        """
        abs_path = self.storage.get_absolute_path(file_path)
        if not os.path.exists(abs_path):
            raise FileNotFoundError(f"Audio file does not exist: {abs_path}")

        filename = os.path.basename(file_path)
        display_name = name or os.path.splitext(filename)[0]

        try:
            meta = await AudioProcessorService.inspect_audio(abs_path)
            duration = meta.duration
            format_name = meta.format_name or meta.codec or "mp3"
            sample_rate = meta.sample_rate
            channels = meta.channels
        except Exception as e:
            logger.warning(f"Failed to inspect audio for {file_path}: {e}")
            duration = 0.0
            format_name = os.path.splitext(file_path)[1].lstrip('.') or "mp3"
            sample_rate = 44100
            channels = 2

        vol = custom_volume if custom_volume is not None else 0.0

        asset = AudioAsset(
            project_id=project_id,
            type=asset_type,
            name=display_name,
            file_path=file_path,
            source_url=source_url,
            duration=duration,
            format=format_name,
            sample_rate=sample_rate,
            channels=channels,
            volume=vol
        )
        db.add(asset)
        await db.commit()
        await db.refresh(asset)
        return asset

    async def list_assets(
        self,
        db: AsyncSession,
        project_id: Optional[uuid.UUID] = None,
        asset_type: Optional[AudioType] = None
    ) -> List[AudioAsset]:
        """
        Lists assets available to a project (project-specific + shared library assets).
        """
        query = select(AudioAsset)
        conditions = []

        if project_id is not None:
            # Include project-specific assets and shared stock library assets (project_id IS NULL)
            conditions.append(or_(AudioAsset.project_id == project_id, AudioAsset.project_id.is_(None)))

        if asset_type is not None:
            conditions.append(AudioAsset.type == asset_type)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(AudioAsset.created_at.desc())
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_asset(self, db: AsyncSession, asset_id: uuid.UUID) -> Optional[AudioAsset]:
        result = await db.execute(select(AudioAsset).where(AudioAsset.id == asset_id))
        return result.scalar_one_or_none()

    async def delete_asset(self, db: AsyncSession, asset_id: uuid.UUID) -> bool:
        asset = await self.get_asset(db, asset_id)
        if not asset:
            return False

        file_path = asset.file_path
        await db.delete(asset)
        await db.commit()

        # Delete local file if present
        if file_path:
            await self.storage.delete_file(file_path)

        return True

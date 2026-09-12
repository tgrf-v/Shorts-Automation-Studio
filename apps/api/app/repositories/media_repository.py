import uuid
from typing import List, Optional, Dict, Any
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.media_asset import MediaAsset, MediaAssetType


class MediaRepository:
    """Repository handling all persistence queries for MediaAsset entities."""

    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        asset_id: uuid.UUID
    ) -> Optional[MediaAsset]:
        stmt = select(MediaAsset).where(MediaAsset.id == asset_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_project(
        db: AsyncSession,
        project_id: uuid.UUID
    ) -> List[MediaAsset]:
        stmt = (
            select(MediaAsset)
            .where(MediaAsset.project_id == project_id)
            .order_by(desc(MediaAsset.created_at))
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def create(
        db: AsyncSession,
        project_id: uuid.UUID,
        asset_type: MediaAssetType,
        filename: str,
        storage_path: str,
        mime_type: str,
        size: int,
        duration: Optional[float] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        fps: Optional[float] = None,
        codec: Optional[str] = None,
        metadata_json: Optional[Dict[str, Any]] = None
    ) -> MediaAsset:
        asset = MediaAsset(
            id=uuid.uuid4(),
            project_id=project_id,
            type=asset_type,
            filename=filename,
            storage_path=storage_path,
            mime_type=mime_type,
            size=size,
            duration=duration,
            width=width,
            height=height,
            fps=fps,
            codec=codec,
            metadata_json=metadata_json or {}
        )
        db.add(asset)
        await db.flush()
        await db.refresh(asset)
        return asset

    @staticmethod
    async def delete(
        db: AsyncSession,
        asset: MediaAsset
    ) -> None:
        await db.delete(asset)
        await db.flush()


media_repository = MediaRepository()

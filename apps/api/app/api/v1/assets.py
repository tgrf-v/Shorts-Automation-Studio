import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.media_asset import MediaAssetResponse
from app.services.project_service import project_service
from app.providers.storage.local import storage_provider

router = APIRouter(prefix="/assets", tags=["Media Assets"])


@router.get(
    "/{asset_id}",
    response_model=MediaAssetResponse,
    summary="Get media asset metadata by ID"
)
async def get_asset(
    asset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> MediaAssetResponse:
    return await project_service.get_asset(db, asset_id)


@router.delete(
    "/{asset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete media asset"
)
async def delete_asset(
    asset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> None:
    await project_service.delete_asset(db, asset_id)


@router.get(
    "/{asset_id}/stream",
    summary="Stream video asset safely for preview"
)
async def stream_asset(
    asset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> FileResponse:
    asset = await project_service.get_asset(db, asset_id)

    full_path = storage_provider.get_full_path(asset.storage_path)
    if not os.path.exists(full_path) or not os.path.isfile(full_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media file is missing from server storage."
        )

    return FileResponse(
        path=full_path,
        media_type=asset.mime_type or "video/mp4",
        filename=asset.filename,
        content_disposition_type="inline"
    )

import os
import uuid
import logging
from typing import List, Tuple, Optional
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.project import Project
from app.models.media_asset import MediaAsset, MediaAssetType
from app.repositories.project_repository import project_repository
from app.repositories.media_repository import media_repository
from app.providers.storage.local import storage_provider
from app.services.media_metadata import media_metadata_service

logger = logging.getLogger("shorts_api.services.project")


class ProjectService:
    """Service handling business rules for projects and media asset uploads."""

    @staticmethod
    async def create_project(db: AsyncSession, name: str) -> Project:
        trimmed = name.strip()
        if not trimmed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project name cannot be empty."
            )
        project = await project_repository.create(db, trimmed)
        await db.commit()
        logger.info(f"Created project: {project.id} ({project.name})")
        return await project_repository.get_by_id(db, project.id)

    @staticmethod
    async def list_projects(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[Project], int]:
        projects = await project_repository.get_all(db, skip=skip, limit=limit)
        return projects, len(projects)

    @staticmethod
    async def get_project(db: AsyncSession, project_id: uuid.UUID) -> Project:
        project = await project_repository.get_by_id(db, project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with ID '{project_id}' not found."
            )
        return project

    @staticmethod
    async def delete_project(db: AsyncSession, project_id: uuid.UUID) -> None:
        project = await ProjectService.get_project(db, project_id)

        # Retrieve all media assets to delete from storage
        assets = await media_repository.get_by_project(db, project_id)
        for asset in assets:
            try:
                await storage_provider.delete(asset.storage_path)
            except Exception as exc:
                logger.warning(f"Error removing storage file for asset {asset.id}: {exc}")

        await project_repository.delete(db, project)
        await db.commit()
        logger.info(f"Deleted project: {project_id} and purged associated media assets.")

    @staticmethod
    async def upload_reference(
        db: AsyncSession,
        project_id: uuid.UUID,
        file: UploadFile
    ) -> MediaAsset:
        project = await ProjectService.get_project(db, project_id)

        # Rule: Do not silently overwrite existing reference
        if project.reference_asset_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project already has a reference video. Remove or replace it explicitly."
            )

        # 1. Validate extension
        filename = file.filename or "reference.mp4"
        ext = os.path.splitext(filename)[1].lower()
        if ext not in settings.ALLOWED_VIDEO_EXTENSIONS:
            allowed = ", ".join(settings.ALLOWED_VIDEO_EXTENSIONS)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format '{ext}'. Allowed formats: {allowed}"
            )

        # 2. Validate MIME type
        content_type = file.content_type or "application/octet-stream"
        if content_type not in settings.ALLOWED_VIDEO_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported MIME type: '{content_type}'."
            )

        # 3. Read content & validate file size
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        file_bytes = await file.read()
        file_size = len(file_bytes)

        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The uploaded file is empty."
            )

        if file_size > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB."
            )

        # 4. Save file to storage
        saved_storage_path = None
        try:
            saved_storage_path = await storage_provider.save(
                project_id=str(project_id),
                category="reference",
                filename=filename,
                content=file_bytes
            )
            full_path = storage_provider.get_full_path(saved_storage_path)

            # 5. Extract metadata with FFprobe
            metadata = await media_metadata_service.extract(full_path)

            # 6. Create media asset record
            asset = await media_repository.create(
                db=db,
                project_id=project_id,
                asset_type=MediaAssetType.REFERENCE,
                filename=filename,
                storage_path=saved_storage_path,
                mime_type=content_type,
                size=file_size,
                duration=metadata.duration,
                width=metadata.width,
                height=metadata.height,
                fps=metadata.fps,
                codec=metadata.codec,
                metadata_json=metadata.raw_info
            )

            # 7. Update project reference pointer
            await project_repository.update_reference(db, project, asset.id)
            await db.commit()

            logger.info(f"Successfully uploaded reference asset {asset.id} for project {project_id}")
            return asset

        except Exception as exc:
            await db.rollback()
            # Cleanup orphaned storage file on failure
            if saved_storage_path:
                logger.warning(f"Cleaning up orphaned storage file {saved_storage_path} due to error: {exc}")
                await storage_provider.delete(saved_storage_path)
            raise exc

    @staticmethod
    async def list_project_assets(
        db: AsyncSession,
        project_id: uuid.UUID
    ) -> List[MediaAsset]:
        # Ensure project exists
        await ProjectService.get_project(db, project_id)
        return await media_repository.get_by_project(db, project_id)

    @staticmethod
    async def get_asset(
        db: AsyncSession,
        asset_id: uuid.UUID
    ) -> MediaAsset:
        asset = await media_repository.get_by_id(db, asset_id)
        if not asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Media asset with ID '{asset_id}' not found."
            )
        return asset

    @staticmethod
    async def delete_asset(
        db: AsyncSession,
        asset_id: uuid.UUID
    ) -> None:
        asset = await ProjectService.get_asset(db, asset_id)
        project = await project_repository.get_by_id(db, asset.project_id)

        # Disallow silent deletion of active reference video
        if project and project.reference_asset_id == asset.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete the active reference video. Delete the project or replace the reference first."
            )

        # Delete from storage first
        await storage_provider.delete(asset.storage_path)

        # Delete database record
        await media_repository.delete(db, asset)
        await db.commit()
        logger.info(f"Deleted media asset: {asset_id}")


project_service = ProjectService()

import uuid
from typing import List, Optional
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.project import Project, ProjectStatus


class ProjectRepository:
    """Repository handling all persistence queries for Project entities."""

    @staticmethod
    async def get_all(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100
    ) -> List[Project]:
        stmt = (
            select(Project)
            .options(selectinload(Project.reference_asset))
            .order_by(desc(Project.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        project_id: uuid.UUID
    ) -> Optional[Project]:
        stmt = (
            select(Project)
            .options(
                selectinload(Project.reference_asset),
                selectinload(Project.media_assets)
            )
            .where(Project.id == project_id)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def create(
        db: AsyncSession,
        name: str
    ) -> Project:
        project = Project(
            id=uuid.uuid4(),
            name=name.strip(),
            status=ProjectStatus.DRAFT
        )
        db.add(project)
        await db.flush()
        await db.refresh(project)
        return project

    @staticmethod
    async def update_reference(
        db: AsyncSession,
        project: Project,
        reference_asset_id: uuid.UUID
    ) -> Project:
        project.reference_asset_id = reference_asset_id
        project.status = ProjectStatus.READY
        await db.flush()
        await db.refresh(project)
        return project

    @staticmethod
    async def delete(
        db: AsyncSession,
        project: Project
    ) -> None:
        await db.delete(project)
        await db.flush()


project_repository = ProjectRepository()

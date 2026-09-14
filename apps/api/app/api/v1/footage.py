import uuid
import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, File, Form, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select, desc, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
from app.models.scene import Scene
from app.models.footage_search import FootageSearch
from app.models.footage_candidate import FootageCandidate
from app.models.scene_footage_selection import SceneFootageSelection
from app.services.footage.footage_service import footage_service
from app.schemas.footage import (
    FootageSearchRequest,
    FootageSearchResponse,
    FootageCandidateSchema,
    SelectCandidateRequest,
    SceneFootageSelectionSchema,
    SceneFootageSummaryItem,
    RangeSelectRequest,
)

router = APIRouter(tags=["Visual Footage Search"])


# 1. Search footage for a scene
@router.post(
    "/scenes/{scene_id}/footage-search",
    response_model=FootageSearchResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Queue a visual footage discovery job for a scene"
)
async def search_footage_for_scene(
    scene_id: uuid.UUID,
    payload: FootageSearchRequest = FootageSearchRequest(),
    db: AsyncSession = Depends(get_db)
) -> FootageSearchResponse:
    try:
        custom_query = payload.query or (payload.queries[0] if payload.queries else None)
        search_record = await footage_service.create_and_enqueue_search(
            db=db,
            scene_id=scene_id,
            query=custom_query,
            provider=payload.provider,
            max_results=payload.max_results
        )
        return FootageSearchResponse(
            search_id=search_record.id,
            scene_id=search_record.scene_id,
            project_id=search_record.project_id,
            query=search_record.query,
            search_provider=search_record.search_provider,
            status=search_record.status.value,
            progress=search_record.progress,
            current_step=search_record.current_step,
            total_results=search_record.total_results,
            error=search_record.error,
            created_at=search_record.created_at
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to queue footage search: {exc}")


# 2. Get search status
@router.get(
    "/footage-searches/{search_id}",
    response_model=FootageSearchResponse,
    summary="Get status and progress of a footage search job"
)
async def get_footage_search(
    search_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> FootageSearchResponse:
    stmt = select(FootageSearch).where(FootageSearch.id == search_id)
    search = (await db.execute(stmt)).scalar_one_or_none()
    if not search:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Footage search '{search_id}' not found.")

    return FootageSearchResponse(
        search_id=search.id,
        scene_id=search.scene_id,
        project_id=search.project_id,
        query=search.query,
        search_provider=search.search_provider,
        status=search.status.value,
        progress=search.progress,
        current_step=search.current_step,
        total_results=search.total_results,
        error=search.error,
        created_at=search.created_at
    )


# 3. Get candidates for a scene
@router.get(
    "/scenes/{scene_id}/footage-candidates",
    response_model=List[FootageCandidateSchema],
    summary="List and rank candidate footage discovered for a scene"
)
async def list_footage_candidates(
    scene_id: uuid.UUID,
    platform: Optional[str] = Query(default=None, description="Filter by platform (youtube, pexels, web)"),
    search_id: Optional[uuid.UUID] = Query(default=None, description="Filter by specific search run"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=30, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
) -> List[FootageCandidateSchema]:
    # Check selection to mark is_selected
    sel_stmt = select(SceneFootageSelection).where(SceneFootageSelection.scene_id == scene_id)
    selection = (await db.execute(sel_stmt)).scalar_one_or_none()
    selected_candidate_id = selection.candidate_id if selection else None

    stmt = select(FootageCandidate).where(FootageCandidate.scene_id == scene_id)
    if platform:
        stmt = stmt.where(FootageCandidate.source_platform == platform.strip().lower())
    if search_id:
        stmt = stmt.where(FootageCandidate.footage_search_id == search_id)

    stmt = stmt.order_by(desc(FootageCandidate.final_score)).offset(skip).limit(limit)
    result = await db.execute(stmt)
    candidates = result.scalars().all()

    output = []
    for c in candidates:
        schema_obj = FootageCandidateSchema(
            id=c.id,
            footage_search_id=c.footage_search_id,
            scene_id=c.scene_id,
            source_platform=c.source_platform,
            source_url=c.source_url,
            video_url=c.video_url,
            title=c.title,
            description=c.description,
            thumbnail_url=c.thumbnail_url,
            creator=c.creator,
            duration=c.duration,
            published_at=c.published_at,
            search_query=c.search_query,
            context_score=c.context_score,
            visual_score=c.visual_score,
            similarity_score=c.similarity_score,
            final_score=c.final_score,
            match_type=c.match_type,
            is_selected=(c.id == selected_candidate_id),
            created_at=c.created_at
        )
        output.append(schema_obj)

    return output


# 4. Get candidate detail
@router.get(
    "/footage-candidates/{candidate_id}",
    response_model=FootageCandidateSchema,
    summary="Get single candidate footage details"
)
async def get_footage_candidate(
    candidate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> FootageCandidateSchema:
    stmt = select(FootageCandidate).where(FootageCandidate.id == candidate_id)
    candidate = (await db.execute(stmt)).scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Footage candidate not found.")

    sel_stmt = select(SceneFootageSelection).where(SceneFootageSelection.candidate_id == candidate_id)
    is_sel = (await db.execute(sel_stmt)).scalar_one_or_none() is not None

    return FootageCandidateSchema(
        id=candidate.id,
        footage_search_id=candidate.footage_search_id,
        scene_id=candidate.scene_id,
        source_platform=candidate.source_platform,
        source_url=candidate.source_url,
        video_url=candidate.video_url,
        title=candidate.title,
        description=candidate.description,
        thumbnail_url=candidate.thumbnail_url,
        creator=candidate.creator,
        duration=candidate.duration,
        published_at=candidate.published_at,
        search_query=candidate.search_query,
        context_score=candidate.context_score,
        visual_score=candidate.visual_score,
        similarity_score=candidate.similarity_score,
        final_score=candidate.final_score,
        match_type=candidate.match_type,
        is_selected=is_sel,
        created_at=candidate.created_at
    )


# 5. Select candidate
@router.post(
    "/footage-candidates/{candidate_id}/select",
    response_model=SceneFootageSelectionSchema,
    summary="Select a candidate video as the chosen footage for its scene"
)
async def select_footage_candidate(
    candidate_id: uuid.UUID,
    payload: SelectCandidateRequest = SelectCandidateRequest(),
    db: AsyncSession = Depends(get_db)
) -> SceneFootageSelectionSchema:
    try:
        selection = await footage_service.select_candidate(
            db=db,
            candidate_id=candidate_id,
            notes=payload.notes
        )
        return selection
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# 6. Get selection for scene
@router.get(
    "/scenes/{scene_id}/footage-selection",
    response_model=Optional[SceneFootageSelectionSchema],
    summary="Get currently selected footage for a scene"
)
async def get_scene_footage_selection(
    scene_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> Optional[SceneFootageSelectionSchema]:
    return await footage_service.get_scene_selection(db, scene_id)


# 7. Search history for scene
@router.get(
    "/scenes/{scene_id}/footage-searches",
    response_model=List[FootageSearchResponse],
    summary="List previous footage searches run for this scene"
)
async def list_scene_footage_searches(
    scene_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> List[FootageSearchResponse]:
    stmt = (
        select(FootageSearch)
        .where(FootageSearch.scene_id == scene_id)
        .order_by(desc(FootageSearch.created_at))
    )
    result = await db.execute(stmt)
    searches = result.scalars().all()

    return [
        FootageSearchResponse(
            search_id=s.id,
            scene_id=s.scene_id,
            project_id=s.project_id,
            query=s.query,
            search_provider=s.search_provider,
            status=s.status.value,
            progress=s.progress,
            current_step=s.current_step,
            total_results=s.total_results,
            error=s.error,
            created_at=s.created_at
        )
        for s in searches
    ]


# 8. Project footage summary overview
@router.get(
    "/projects/{project_id}/footage/summary",
    response_model=List[SceneFootageSummaryItem],
    summary="Overview of all scenes in project with selection status and candidates count"
)
async def get_project_footage_summary(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> List[SceneFootageSummaryItem]:
    stmt = (
        select(Scene)
        .where(Scene.project_id == project_id)
        .order_by(Scene.sequence)
    )
    result = await db.execute(stmt)
    scenes = result.scalars().all()

    summary_items = []
    for sc in scenes:
        # Count candidates
        c_count_stmt = select(func.count(FootageCandidate.id)).where(FootageCandidate.scene_id == sc.id)
        total_cand = (await db.execute(c_count_stmt)).scalar() or 0

        # Get selection
        sel = await footage_service.get_scene_selection(db, sc.id)
        cand_schema = None
        if sel and sel.candidate:
            c = sel.candidate
            cand_schema = FootageCandidateSchema(
                id=c.id,
                footage_search_id=c.footage_search_id,
                scene_id=c.scene_id,
                source_platform=c.source_platform,
                source_url=c.source_url,
                video_url=c.video_url,
                title=c.title,
                description=c.description,
                thumbnail_url=c.thumbnail_url,
                creator=c.creator,
                duration=c.duration,
                published_at=c.published_at,
                search_query=c.search_query,
                context_score=c.context_score,
                visual_score=c.visual_score,
                similarity_score=c.similarity_score,
                final_score=c.final_score,
                match_type=c.match_type,
                is_selected=True,
                created_at=c.created_at
            )

        summary_items.append(
            SceneFootageSummaryItem(
                scene_id=sc.id,
                sequence=sc.sequence,
                start_time=sc.start_time,
                end_time=sc.end_time,
                duration=sc.duration,
                description=sc.description,
                total_candidates=total_cand,
                has_selection=bool(sel),
                selected_candidate=cand_schema
            )
        )

    return summary_items


# 9. Create Custom Footage Candidate (Upload File or Direct Link)
@router.post(
    "/scenes/{scene_id}/custom-footage",
    response_model=FootageCandidateSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Upload custom video clip (MP4) or add direct video link (TikTok/IG) for a scene"
)
async def create_custom_footage(
    scene_id: uuid.UUID,
    file: Optional[UploadFile] = File(None),
    video_url: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    platform: Optional[str] = Form(None),
    start_sequence: Optional[int] = Form(None),
    end_sequence: Optional[int] = Form(None),
    db: AsyncSession = Depends(get_db)
) -> FootageCandidateSchema:
    try:
        file_bytes = None
        filename = None
        if file and file.filename:
            filename = file.filename
            file_bytes = await file.read()

        if not file_bytes and (not video_url or not video_url.strip()):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Must provide either a video file upload or a video URL."
            )

        candidate = await footage_service.create_custom_footage_candidate(
            db=db,
            scene_id=scene_id,
            file_bytes=file_bytes,
            filename=filename,
            video_url=video_url.strip() if video_url else None,
            title=title.strip() if title else None,
            platform=platform.strip() if platform else None,
            start_sequence=start_sequence,
            end_sequence=end_sequence
        )

        return FootageCandidateSchema(
            id=candidate.id,
            footage_search_id=candidate.footage_search_id,
            scene_id=candidate.scene_id,
            source_platform=candidate.source_platform,
            source_url=candidate.source_url,
            video_url=candidate.video_url,
            title=candidate.title,
            description=candidate.description,
            thumbnail_url=candidate.thumbnail_url,
            creator=candidate.creator,
            duration=candidate.duration,
            published_at=candidate.published_at,
            search_query=candidate.search_query,
            context_score=candidate.context_score,
            visual_score=candidate.visual_score,
            similarity_score=candidate.similarity_score,
            final_score=candidate.final_score,
            match_type=candidate.match_type,
            is_selected=True,
            created_at=candidate.created_at
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to process custom footage: {exc}")


# 10. Select Candidate for a Range of Scenes
@router.post(
    "/footage-candidates/{candidate_id}/range-select",
    response_model=List[SceneFootageSelectionSchema],
    summary="Assign candidate footage across a range of scenes"
)
async def select_candidate_for_range(
    candidate_id: uuid.UUID,
    payload: RangeSelectRequest,
    db: AsyncSession = Depends(get_db)
) -> List[SceneFootageSelectionSchema]:
    try:
        selections = await footage_service.select_candidate_for_range(
            db=db,
            candidate_id=candidate_id,
            start_sequence=payload.start_sequence,
            end_sequence=payload.end_sequence,
            project_id=payload.project_id
        )
        return [
            SceneFootageSelectionSchema(
                id=s.id,
                scene_id=s.scene_id,
                candidate_id=s.candidate_id,
                status=s.status,
                notes=s.notes,
                created_at=s.created_at,
                updated_at=s.updated_at
            )
            for s in selections
        ]
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to assign footage range: {exc}")


# 11. Serve Custom Footage Thumbnail
@router.get(
    "/footage-candidates/{candidate_id}/thumbnail",
    summary="Serve candidate thumbnail image safely by candidate ID"
)
async def get_candidate_thumbnail(
    candidate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(FootageCandidate).where(FootageCandidate.id == candidate_id)
    cand = (await db.execute(stmt)).scalar_one_or_none()
    if not cand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found.")

    sc_stmt = select(Scene).where(Scene.id == cand.scene_id)
    scene = (await db.execute(sc_stmt)).scalar_one_or_none()
    if not scene:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scene not found.")

    storage_dir = os.path.join(settings.MEDIA_STORAGE_PATH, "projects", str(scene.project_id), "footage")
    thumb_path = os.path.join(storage_dir, f"{cand.id}_thumb.jpg")
    if os.path.exists(thumb_path):
        return FileResponse(thumb_path, media_type="image/jpeg")

    # Fallback to 404
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thumbnail file not found.")

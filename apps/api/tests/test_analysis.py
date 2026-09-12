import os
import uuid
import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.core.database import Base, get_db
from app.models.project import Project, ProjectStatus
from app.models.media_asset import MediaAsset, MediaAssetType
from app.models.analysis_job import AnalysisJob, AnalysisJobStatus, AnalysisJobStep
from app.services.analysis.transcription import MockSTTProvider, TranscriptSegment
from app.services.analysis.scene_detection import SceneDetectionService
from app.services.analysis.scene_description import HeuristicVisionProvider



@pytest.mark.anyio
async def test_transcription_provider_schema():
    provider = MockSTTProvider()
    result = await provider.transcribe("dummy_audio.wav")

    assert result.language == "en"
    assert len(result.segments) == 3
    assert len(result.text) > 0

    for seg in result.segments:
        assert isinstance(seg.start, float)
        assert isinstance(seg.end, float)
        assert seg.end > seg.start
        assert len(seg.text) > 0


@pytest.mark.anyio
async def test_scene_detection_and_alignment():
    service = SceneDetectionService()

    raw_scenes = [
        {"start_time": 0.0, "end_time": 3.0, "duration": 3.0},
        {"start_time": 3.0, "end_time": 6.5, "duration": 3.5},
        {"start_time": 6.5, "end_time": 10.0, "duration": 3.5},
    ]

    segments = [
        TranscriptSegment(start=0.5, end=2.5, text="Hello world"),
        TranscriptSegment(start=2.8, end=4.5, text="This overlaps scene 1 and 2"),
        TranscriptSegment(start=7.0, end=9.0, text="Final sentence"),
    ]

    aligned = service.align_transcript(raw_scenes, segments)
    assert len(aligned) == 3

    # Scene 1 (0 - 3s): should contain segment 0 (0.5-2.5) and segment 1 (2.8-4.5)
    assert aligned[0].sequence == 1
    assert aligned[0].start_time == 0.0
    assert aligned[0].end_time == 3.0
    assert aligned[0].duration == 3.0
    assert len(aligned[0].transcript_segments) == 2
    assert aligned[0].transcript_segments[0]["text"] == "Hello world"
    assert aligned[0].transcript_segments[1]["text"] == "This overlaps scene 1 and 2"

    # Scene 2 (3 - 6.5s): should contain segment 1 (2.8-4.5)
    assert aligned[1].sequence == 2
    assert len(aligned[1].transcript_segments) == 1
    assert aligned[1].transcript_segments[0]["text"] == "This overlaps scene 1 and 2"

    # Scene 3 (6.5 - 10s): should contain segment 2 (7.0-9.0)
    assert aligned[2].sequence == 3
    assert len(aligned[2].transcript_segments) == 1
    assert aligned[2].transcript_segments[0]["text"] == "Final sentence"


@pytest.mark.anyio
async def test_scene_description_provider():
    provider = HeuristicVisionProvider()
    context = "A fast red car races across an empty highway."
    result = await provider.describe_scene([], context)

    assert result.description is not None
    assert len(result.description) > 0
    assert isinstance(result.objects, list)
    assert len(result.objects) > 0
    assert isinstance(result.actions, list)
    assert result.environment is not None


@pytest.mark.anyio
async def test_analysis_api_validation_and_errors():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Non-existent project
        fake_id = str(uuid.uuid4())
        res_404 = await client.post(f"/api/v1/projects/{fake_id}/analyze")
        assert res_404.status_code == 400

        # 2. Project without reference video
        create_res = await client.post("/api/v1/projects", json={"name": "No Reference Video"})
        assert create_res.status_code == 201
        proj_id = create_res.json()["id"]

        no_ref_res = await client.post(f"/api/v1/projects/{proj_id}/analyze")
        assert no_ref_res.status_code == 400
        assert "reference video" in no_ref_res.json()["detail"].lower()

        # 3. Get analysis for project with no analysis yet
        get_res = await client.get(f"/api/v1/projects/{proj_id}/analysis")
        assert get_res.status_code == 200
        analysis_data = get_res.json()
        assert analysis_data["project_id"] == proj_id
        assert analysis_data["transcript"] is None
        assert len(analysis_data["scenes"]) == 0

        # 4. Get non-existent analysis job
        job_404 = await client.get(f"/api/v1/analysis-jobs/{fake_id}")
        assert job_404.status_code == 404

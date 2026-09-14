import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.main import app
from app.core.database import Base, get_db
from app.models.project import Project, ProjectStatus
from app.models.media_asset import MediaAsset, MediaAssetType
from app.models.transcript import Transcript
from app.models.scene import Scene
from app.models.script import Script, ScriptStatus
from app.models.script_job import ScriptJob, ScriptJobStatus
from app.providers.script.base import (
    ScriptGenerationContext,
    SceneContextItem,
    GeneratedScriptPayload,
    GeneratedSceneSegment,
)
from app.providers.script.mock import MockScriptProvider
from app.services.script.duration import (
    count_words,
    calculate_speaking_duration,
    calculate_duration_ratio,
    is_duration_within_bounds,
    calculate_duration_diff_percentage,
)
from app.services.script.script_service import script_service


@pytest.mark.anyio
async def test_duration_estimation_calculator():
    """Tests speaking duration calculation, ratios, and tolerance checks."""
    text_sample = "Ini adalah contoh naskah narasi YouTube Shorts yang sangat menarik dan cepat."
    words = count_words(text_sample)
    assert words == 12

    # At 150 WPM: (12 / 150) * 60 = 4.8 seconds
    est_duration = calculate_speaking_duration(text_sample, target_wpm=150)
    assert est_duration == 4.8

    # Duration ratio against source duration (5.0s) -> 4.8 / 5.0 = 0.96
    ratio = calculate_duration_ratio(est_duration, 5.0)
    assert ratio == 0.96
    assert is_duration_within_bounds(ratio, min_ratio=0.85, max_ratio=1.15) is True

    # Diff percentage: ((4.8 - 5.0) / 5.0) * 100 = -4.0%
    diff = calculate_duration_diff_percentage(est_duration, 5.0)
    assert diff == -4.0

    # Out of bounds check: 100 words (40s) vs source 10s -> ratio 4.0
    out_ratio = calculate_duration_ratio(40.0, 10.0)
    assert is_duration_within_bounds(out_ratio, min_ratio=0.85, max_ratio=1.15) is False


@pytest.mark.anyio
async def test_mock_script_provider_output():
    """Verifies that MockScriptProvider outputs structured, scene-aligned Indonesian scripts."""
    provider = MockScriptProvider()
    scenes = [
        SceneContextItem(
            scene_id=str(uuid.uuid4()),
            sequence=1,
            start_time=0.0,
            end_time=3.5,
            duration=3.5,
            visual_description="A man discovers a deep underwater cave.",
            source_dialogue="Scientists made an astonishing discovery underwater."
        ),
        SceneContextItem(
            scene_id=str(uuid.uuid4()),
            sequence=2,
            start_time=3.5,
            end_time=7.0,
            duration=3.5,
            visual_description="Bioluminescent creatures swimming.",
            source_dialogue="Entirely new ecosystems thrive in the darkness."
        )
    ]

    context = ScriptGenerationContext(
        project_name="Deep Ocean Mystery",
        source_language="en",
        target_language="id",
        source_transcript_full="Scientists made an astonishing discovery underwater. Entirely new ecosystems thrive in the darkness.",
        scenes=scenes,
        target_wpm=150
    )

    payload = await provider.generate_script(context)

    assert isinstance(payload, GeneratedScriptPayload)
    assert len(payload.title) > 0
    assert len(payload.full_script) > 0
    assert len(payload.segments) == 2
    assert payload.segments[0].scene_id == scenes[0].scene_id
    assert payload.segments[1].scene_id == scenes[1].scene_id
    assert len(payload.segments[0].adapted_text) > 0


@pytest.mark.anyio
async def test_script_service_create_job_and_generate():
    """Tests the full background generation pipeline using Mock provider and Async database."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create Project
        p_res = await client.post("/api/v1/projects", json={"name": "Science Mystery Short"})
        assert p_res.status_code == 201
        project_id = p_res.json()["id"]

        # 2. Upload Reference Video
        dummy_video = ("ref.mp4", b"\x00\x00\x00\x20ftypmp42" + b"\x00" * 2000, "video/mp4")
        up_res = await client.post(f"/api/v1/projects/{project_id}/reference", files={"file": dummy_video})
        assert up_res.status_code == 201
        asset_id = up_res.json()["id"]

        # 3. Simulate Analysis Results (insert Transcript and Scenes manually into test db)
        async for db in app.dependency_overrides[get_db]():
            tr = Transcript(
                project_id=uuid.UUID(project_id),
                media_asset_id=uuid.UUID(asset_id),
                language="en",
                provider="mock",
                content="Scientists recently made an astonishing discovery. New ecosystems thrive deep below.",
                segments=[
                    {"start": 0.0, "end": 3.0, "text": "Scientists recently made an astonishing discovery."},
                    {"start": 3.0, "end": 6.0, "text": "New ecosystems thrive deep below."}
                ]
            )
            db.add(tr)

            sc1 = Scene(
                project_id=uuid.UUID(project_id),
                sequence=1,
                start_time=0.0,
                end_time=3.0,
                duration=3.0,
                description="Visual of underwater trench",
                transcript_segment=[{"start": 0.0, "end": 3.0, "text": "Scientists recently made an astonishing discovery."}]
            )
            sc2 = Scene(
                project_id=uuid.UUID(project_id),
                sequence=2,
                start_time=3.0,
                end_time=6.0,
                duration=3.0,
                description="Creatures glowing",
                transcript_segment=[{"start": 3.0, "end": 6.0, "text": "New ecosystems thrive deep below."}]
            )
            db.add(sc1)
            db.add(sc2)
            await db.commit()
            break

        # 4. Trigger Script Generation via API
        gen_res = await client.post(
            f"/api/v1/projects/{project_id}/scripts/generate",
            json={"provider": "mock"}
        )
        assert gen_res.status_code == 202
        gen_data = gen_res.json()
        job_id = gen_data["job_id"]
        script_id = gen_data["script_id"]
        assert gen_data["status"] == "queued"

        # 5. Process Job with Worker Service
        await script_service.process_job(job_id)

        # 6. Check Job Status via API
        job_res = await client.get(f"/api/v1/script-jobs/{job_id}")
        assert job_res.status_code == 200
        job_info = job_res.json()
        assert job_info["status"] == "completed"
        assert job_info["progress"] == 100

        # 7. Check Script Details
        script_res = await client.get(f"/api/v1/scripts/{script_id}")
        assert script_res.status_code == 200
        script_data = script_res.json()
        assert script_data["status"] == "ready"
        assert script_data["version"] == 1
        assert script_data["is_active"] is True
        assert len(script_data["title"]) > 0
        assert len(script_data["content"]) > 0
        assert len(script_data["segments"]) == 2
        assert script_data["estimated_duration"] > 0


@pytest.mark.anyio
async def test_script_versioning_and_activation():
    """Verifies that multiple generations create separate versions and activation works correctly."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create Project
        p_res = await client.post("/api/v1/projects", json={"name": "Versioning Test"})
        project_id = p_res.json()["id"]

        # Add mock transcript and scene
        async for db in app.dependency_overrides[get_db]():
            tr = Transcript(
                project_id=uuid.UUID(project_id),
                media_asset_id=uuid.uuid4(),
                language="en",
                provider="mock",
                content="Sample transcript",
                segments=[]
            )
            db.add(tr)
            sc = Scene(
                project_id=uuid.UUID(project_id),
                sequence=1,
                start_time=0.0,
                end_time=4.0,
                duration=4.0,
                transcript_segment=[]
            )
            db.add(sc)
            await db.commit()
            break

        # Generate Version 1
        v1_res = await client.post(f"/api/v1/projects/{project_id}/scripts/generate", json={"provider": "mock"})
        assert v1_res.status_code == 202
        v1_id = v1_res.json()["script_id"]
        await script_service.process_job(v1_res.json()["job_id"])

        # Generate Version 2
        v2_res = await client.post(f"/api/v1/projects/{project_id}/scripts/generate", json={"provider": "mock"})
        assert v2_res.status_code == 202
        v2_id = v2_res.json()["script_id"]
        await script_service.process_job(v2_res.json()["job_id"])

        # List scripts: should have 2 versions
        list_res = await client.get(f"/api/v1/projects/{project_id}/scripts")
        assert list_res.status_code == 200
        scripts = list_res.json()
        assert len(scripts) == 2
        assert scripts[0]["version"] == 2
        assert scripts[1]["version"] == 1

        # Activate Version 1
        act_res = await client.post(f"/api/v1/scripts/{v1_id}/activate")
        assert act_res.status_code == 200
        assert act_res.json()["is_active"] is True

        # Check that Version 2 is now inactive
        v2_check = await client.get(f"/api/v1/scripts/{v2_id}")
        assert v2_check.json()["is_active"] is False


@pytest.mark.anyio
async def test_script_manual_patch_and_recalculation():
    """Verifies that PATCH updates content, marks is_manually_edited, and recalculates duration without calling AI."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        p_res = await client.post("/api/v1/projects", json={"name": "Manual Edit Test"})
        project_id = p_res.json()["id"]

        async for db in app.dependency_overrides[get_db]():
            tr = Transcript(
                project_id=uuid.UUID(project_id),
                media_asset_id=uuid.uuid4(),
                language="en",
                provider="mock",
                content="Short transcript",
                segments=[]
            )
            db.add(tr)
            sc = Scene(
                project_id=uuid.UUID(project_id),
                sequence=1,
                start_time=0.0,
                end_time=5.0,
                duration=5.0,
                transcript_segment=[]
            )
            db.add(sc)
            await db.commit()
            break

        gen_res = await client.post(f"/api/v1/projects/{project_id}/scripts/generate", json={"provider": "mock"})
        script_id = gen_res.json()["script_id"]
        await script_service.process_job(gen_res.json()["job_id"])

        # PATCH title and content
        new_title = "Judul Baru Yang Diedit Creator"
        new_content = "Satu dua tiga empat lima enam tujuh delapan sembilan sepuluh."
        patch_res = await client.patch(
            f"/api/v1/scripts/{script_id}",
            json={
                "title": new_title,
                "content": new_content
            }
        )
        assert patch_res.status_code == 200
        updated = patch_res.json()
        assert updated["title"] == new_title
        assert updated["content"] == new_content
        assert updated["is_manually_edited"] is True
        assert updated["word_count"] == 10
        # (10 / 150) * 60 = 4.0 seconds
        assert updated["estimated_duration"] == 4.0


@pytest.mark.anyio
async def test_script_api_validation_errors():
    """Verifies error handling for missing projects, transcripts, or invalid inputs."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Non-existent project
        fake_id = str(uuid.uuid4())
        res_400 = await client.post(f"/api/v1/projects/{fake_id}/scripts/generate")
        assert res_400.status_code == 400

        # Project without analysis
        p_res = await client.post("/api/v1/projects", json={"name": "Empty Project"})
        proj_id = p_res.json()["id"]

        no_trans_res = await client.post(f"/api/v1/projects/{proj_id}/scripts/generate")
        assert no_trans_res.status_code == 400
        assert "transcript" in no_trans_res.json()["detail"].lower()

        # Non-existent script GET and PATCH
        get_404 = await client.get(f"/api/v1/scripts/{fake_id}")
        assert get_404.status_code == 404

        patch_404 = await client.patch(f"/api/v1/scripts/{fake_id}", json={"title": "Test"})
        assert patch_404.status_code == 404


@pytest.mark.anyio
async def test_gemini_provider_selection_and_config():
    """Verifies that provider selection and model configuration work accurately."""
    from app.providers.script import get_script_provider
    from app.providers.script.gemini import GeminiScriptProvider
    from app.providers.script.mock import MockScriptProvider
    from app.core.config import settings

    # 1. Provider selection
    gemini_p = get_script_provider("gemini")
    assert isinstance(gemini_p, GeminiScriptProvider)
    assert gemini_p.model == (settings.SCRIPT_MODEL or "gemini-2.5-flash")

    mock_p = get_script_provider("mock")
    assert isinstance(mock_p, MockScriptProvider)

    # 2. Missing key error handling
    empty_key_provider = GeminiScriptProvider(api_key="")
    ctx = ScriptGenerationContext(
        project_name="Test Project",
        source_transcript_full="Test transcript",
        scenes=[]
    )
    with pytest.raises(ValueError, match="GEMINI_API_KEY is not configured"):
        await empty_key_provider.generate_script(ctx)


@pytest.mark.anyio
async def test_gemini_provider_structured_output_mocked(monkeypatch):
    """Verifies Gemini output parsing and validation against mocked HTTP responses."""
    import httpx
    from app.providers.script.gemini import GeminiScriptProvider

    sample_gemini_json = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": (
                                '{\n'
                                '  "title": "Rahasia Dasar Laut Yang Terungkap",\n'
                                '  "full_script": "Tahukah kamu misteri terbesar di kedalaman laut? Simak faktanya sampai habis!",\n'
                                '  "segments": [\n'
                                '    {\n'
                                '      "scene_id": "scene_001",\n'
                                '      "adapted_text": "Tahukah kamu misteri terbesar di kedalaman laut?"\n'
                                '    },\n'
                                '    {\n'
                                '      "scene_id": "scene_002",\n'
                                '      "adapted_text": "Simak faktanya sampai habis!"\n'
                                '    }\n'
                                '  ]\n'
                                '}'
                            )
                        }
                    ]
                }
            }
        ]
    }

    class MockResponse:
        status_code = 200
        def json(self):
            return sample_gemini_json
        def raise_for_status(self):
            pass

    async def mock_post(*args, **kwargs):
        return MockResponse()

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    provider = GeminiScriptProvider(api_key="mock_valid_key", model="gemini-2.5-flash")
    ctx = ScriptGenerationContext(
        project_name="Ocean",
        source_transcript_full="Original ocean text",
        scenes=[
            SceneContextItem(scene_id="scene_001", sequence=1, start_time=0.0, end_time=3.0, duration=3.0),
            SceneContextItem(scene_id="scene_002", sequence=2, start_time=3.0, end_time=6.0, duration=3.0)
        ]
    )

    payload = await provider.generate_script(ctx)
    assert payload.title == "Rahasia Dasar Laut Yang Terungkap"
    assert "Tahukah kamu" in payload.full_script
    assert len(payload.segments) == 2
    assert payload.segments[0].scene_id == "scene_001"
    assert payload.segments[1].scene_id == "scene_002"


@pytest.mark.anyio
async def test_gemini_provider_error_handling(monkeypatch):
    """Verifies that API error codes (401, 429) produce clear user-friendly messages without exposing keys."""
    import httpx
    from app.providers.script.gemini import GeminiScriptProvider

    class MockErrorResponse:
        def __init__(self, status_code: int, msg: str):
            self.status_code = status_code
            self._msg = msg
            self.text = msg
        def json(self):
            return {"error": {"code": self.status_code, "message": self._msg}}

    # Test 401/403
    async def mock_401(*args, **kwargs):
        return MockErrorResponse(401, "API_KEY_INVALID")

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_401)
    provider = GeminiScriptProvider(api_key="test_key_12345", model="gemini-2.5-flash")
    ctx = ScriptGenerationContext(project_name="Test", source_transcript_full="Text", scenes=[])

    with pytest.raises(ValueError, match="Invalid Google Gemini API key"):
        await provider.generate_script(ctx)

    # Test 429
    async def mock_429(*args, **kwargs):
        return MockErrorResponse(429, "Resource has been exhausted")

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_429)
    with pytest.raises(RuntimeError, match="quota exceeded"):
        await provider.generate_script(ctx)

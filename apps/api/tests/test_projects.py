import os
import uuid
import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.core.database import Base, get_db
from app.providers.storage.local import LocalStorageProvider
from app.services.media_metadata import MediaMetadataService

# Use temporary sqlite database for tests
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(autouse=True)
def setup_test_db():
    async def _init():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def _cleanup():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    asyncio.run(_init())
    yield
    asyncio.run(_cleanup())


async def override_get_db():
    async with TestSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest.mark.anyio
async def test_storage_provider_crud(tmp_path):
    storage = LocalStorageProvider(base_path=str(tmp_path))
    content = b"fake video content for testing storage"
    proj_id = str(uuid.uuid4())

    # 1. Save
    rel_path = await storage.save(proj_id, "reference", "test_video.mp4", content)
    assert "test_video.mp4" in rel_path

    # 2. Exists
    exists = await storage.exists(rel_path)
    assert exists is True

    # 3. Path resolution & content verification
    full_path = storage.get_full_path(rel_path)
    assert os.path.exists(full_path)
    with open(full_path, "rb") as f:
        assert f.read() == content

    # 4. Delete
    deleted = await storage.delete(rel_path)
    assert deleted is True
    assert await storage.exists(rel_path) is False


@pytest.mark.anyio
async def test_metadata_extraction_fallback(tmp_path):
    dummy_file = tmp_path / "sample.mp4"
    dummy_bytes = b"\x00\x00\x00\x20ftypmp42" + b"\x00" * 1000
    dummy_file.write_bytes(dummy_bytes)


    metadata = await MediaMetadataService.extract(str(dummy_file))
    assert metadata.size == len(dummy_bytes)
    assert metadata.container is not None



@pytest.mark.anyio
async def test_project_crud_api():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create project
        create_res = await client.post("/api/v1/projects", json={"name": "Viral Physics Short"})
        assert create_res.status_code == 201
        data = create_res.json()
        assert data["name"] == "Viral Physics Short"
        assert data["status"] == "draft"
        project_id = data["id"]

        # 2. List projects
        list_res = await client.get("/api/v1/projects")
        assert list_res.status_code == 200
        list_data = list_res.json()
        assert list_data["total"] >= 1
        assert any(p["id"] == project_id for p in list_data["projects"])

        # 3. Get single project
        get_res = await client.get(f"/api/v1/projects/{project_id}")
        assert get_res.status_code == 200
        assert get_res.json()["id"] == project_id

        # 4. Get non-existent project (404)
        random_id = str(uuid.uuid4())
        not_found_res = await client.get(f"/api/v1/projects/{random_id}")
        assert not_found_res.status_code == 404

        # 5. Delete project
        del_res = await client.delete(f"/api/v1/projects/{project_id}")
        assert del_res.status_code == 204

        # Verify deletion
        verify_res = await client.get(f"/api/v1/projects/{project_id}")
        assert verify_res.status_code == 404


@pytest.mark.anyio
async def test_reference_upload_and_streaming():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create project
        create_res = await client.post("/api/v1/projects", json={"name": "Upload Test Project"})
        assert create_res.status_code == 201
        project_id = create_res.json()["id"]

        # 2. Upload invalid extension (.txt)
        bad_file = ("notes.txt", b"invalid content", "text/plain")
        bad_upload = await client.post(
            f"/api/v1/projects/{project_id}/reference",
            files={"file": bad_file}
        )
        assert bad_upload.status_code == 400

        # 3. Upload valid video reference (.mp4)
        sample_video_bytes = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42mp41" + b"\x00" * 4096
        good_file = ("ref_video.mp4", sample_video_bytes, "video/mp4")
        upload_res = await client.post(
            f"/api/v1/projects/{project_id}/reference",
            files={"file": good_file}
        )
        assert upload_res.status_code == 201
        asset_data = upload_res.json()
        assert asset_data["filename"] == "ref_video.mp4"
        assert asset_data["mime_type"] == "video/mp4"
        assert asset_data["size"] == len(sample_video_bytes)
        asset_id = asset_data["id"]

        # 4. Verify project reference_asset_id is updated and status is ready
        proj_res = await client.get(f"/api/v1/projects/{project_id}")
        assert proj_res.status_code == 200
        proj_data = proj_res.json()
        assert proj_data["reference_asset_id"] == asset_id
        assert proj_data["status"] == "ready"
        assert proj_data["reference_asset"]["id"] == asset_id

        # 5. Reject duplicate reference upload
        dup_file = ("second_ref.mp4", sample_video_bytes, "video/mp4")
        dup_res = await client.post(
            f"/api/v1/projects/{project_id}/reference",
            files={"file": dup_file}
        )
        assert dup_res.status_code == 400

        # 6. Stream video asset
        stream_res = await client.get(f"/api/v1/assets/{asset_id}/stream")
        assert stream_res.status_code == 200
        assert stream_res.headers["content-type"] == "video/mp4"
        assert len(stream_res.content) == len(sample_video_bytes)

        # 7. Disallow silent deletion of active reference video
        del_asset_res = await client.delete(f"/api/v1/assets/{asset_id}")
        assert del_asset_res.status_code == 400

        # 8. Deleting project cascades and removes assets
        del_proj_res = await client.delete(f"/api/v1/projects/{project_id}")
        assert del_proj_res.status_code == 204

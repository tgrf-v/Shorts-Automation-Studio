import os
import sys
import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

_curr = os.path.dirname(os.path.abspath(__file__))
_root = os.path.abspath(os.path.join(_curr, ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from app.main import app
from app.core.database import Base, get_db
import app.core.database as db_mod
from sqlalchemy.pool import StaticPool

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
db_mod.engine = test_engine
db_mod.AsyncSessionLocal = TestSessionLocal

import app.services.script.script_service as ss_mod
ss_mod.AsyncSessionLocal = TestSessionLocal


async def override_get_db():
    async with TestSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


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


@pytest.fixture(autouse=True)
def mock_redis_queues(monkeypatch):
    try:
        from app.services.script.queue import script_queue
        monkeypatch.setattr(script_queue, "enqueue", lambda *args, **kwargs: True)
    except Exception:
        pass
    try:
        from app.services.tts.queue import tts_queue
        monkeypatch.setattr(tts_queue, "enqueue", lambda *args, **kwargs: True)
    except Exception:
        pass
    try:
        from app.services.footage.queue import footage_queue
        monkeypatch.setattr(footage_queue, "enqueue", lambda *args, **kwargs: True)
    except Exception:
        pass
    try:
        from app.services.analysis.queue import analysis_queue
        monkeypatch.setattr(analysis_queue, "enqueue", lambda *args, **kwargs: True)
    except Exception:
        pass


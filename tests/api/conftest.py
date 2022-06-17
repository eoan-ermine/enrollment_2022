import pytest
import pytest_asyncio
from alembic.command import upgrade
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from analyzer.api.app import app, get_session


@pytest.fixture
def migrated_sqlite(alembic_config, sqlite):
    upgrade(alembic_config, "head")
    return sqlite


@pytest_asyncio.fixture
async def session(migrated_sqlite):
    engine = create_async_engine(migrated_sqlite.replace("sqlite", "sqlite+aiosqlite"), future=True)
    SessionLocal = sessionmaker(
        bind=engine, autocommit=False, autoflush=False, expire_on_commit=False, class_=AsyncSession
    )
    async with SessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client(session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = AsyncClient(app=app, base_url="http://test")
    try:
        yield client
    finally:
        await client.aclose()
    app.dependency_overrides.clear()

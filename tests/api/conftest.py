import pytest
import pytest_asyncio
from alembic.command import upgrade
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from analyzer.api.app import app, get_session


@pytest.fixture
def migrated_postgres(alembic_config, postgres):
    upgrade(alembic_config, "head")
    return postgres


@pytest_asyncio.fixture
async def session(migrated_postgres):
    engine = create_async_engine(migrated_postgres.replace("psycopg2", "asyncpg"), future=True)
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

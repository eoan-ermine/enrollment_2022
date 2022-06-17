import pytest
from alembic.command import upgrade
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from analyzer.api.app import app, get_session
from analyzer.db.core import ASYNCHRONOUS_DATABASE_URL


@pytest.fixture
async def migrated_sqlite(alembic_config, sqlite):
    upgrade(alembic_config, "head")
    return sqlite


@pytest.fixture
def session(migrated_sqlite):
    engine = create_async_engine(ASYNCHRONOUS_DATABASE_URL, future=True)
    SessionLocal = sessionmaker(
        bind=engine, autocommit=False, autoflush=False, expire_on_commit=False, class_=AsyncSession
    )
    with SessionLocal() as session:
        yield session


@pytest.fixture
def client(session):
    app.depencdency_overrides[get_session] = session
    client = TestClient(app)
    yield client
    app.depencdency_overrides.clear()

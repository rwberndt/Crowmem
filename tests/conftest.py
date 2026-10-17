import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401 -- registers every model on Base.metadata
from app.core.config import get_settings
from app.core.db import get_db
from app.core.scoring_config import get_scoring_config
from app.embeddings.fastembed_client import get_embedding_client
from app.main import app as fastapi_app
from app.models.base import Base
from tests.fixtures.fake_embedding_client import FakeEmbeddingClient


@pytest.fixture(scope="session")
def db_engine():
    url = get_settings().test_database_url
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(db_engine) -> Session:
    connection = db_engine.connect()
    transaction = connection.begin()
    session_factory = sessionmaker(bind=connection, autoflush=False, expire_on_commit=False)
    session = session_factory()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def fake_embedding_client() -> FakeEmbeddingClient:
    return FakeEmbeddingClient()


@pytest.fixture
def client(db_session, fake_embedding_client):
    fastapi_app.dependency_overrides[get_db] = lambda: db_session
    fastapi_app.dependency_overrides[get_embedding_client] = lambda: fake_embedding_client
    with TestClient(fastapi_app) as test_client:
        yield test_client
    fastapi_app.dependency_overrides.clear()


@pytest.fixture
def scoring_config():
    return get_scoring_config()

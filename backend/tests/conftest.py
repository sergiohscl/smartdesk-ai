from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.database import get_session
from app.main import app


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.add = MagicMock()

    return session


@pytest_asyncio.fixture
async def client(mock_session):
    async def override_get_session():
        yield mock_session

    app.dependency_overrides[get_session] = override_get_session

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url='http://test',
        ) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_session, None)

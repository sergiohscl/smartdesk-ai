from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import jwt
import pytest
from httpx import AsyncClient

from app.core.security import create_access_token, hash_password
from app.core.settings import get_settings
from app.models.user import User


def make_user(is_active: bool = True) -> User:
    return User(
        id=1,
        name='Usuario Teste',
        email='usuario@teste.com',
        hashed_password=hash_password('SenhaSegura123'),
        is_active=is_active,
        created_at=datetime.now(UTC),
    )


def mock_user_query(mock_session, user):
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    mock_session.execute.return_value = result


@pytest.mark.asyncio
async def test_get_me_success(
    client: AsyncClient,
    mock_session,
):
    user = make_user()
    mock_user_query(mock_session, user)

    token = create_access_token(subject=str(user.id))

    response = await client.get(
        '/api/v1/users/me',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == 200

    data = response.json()

    assert data['id'] == user.id
    assert data['name'] == user.name
    assert data['email'] == user.email
    assert data['is_active'] is True
    assert 'hashed_password' not in data


@pytest.mark.asyncio
async def test_get_me_without_token(
    client: AsyncClient,
    mock_session,
):
    response = await client.get('/api/v1/users/me')

    assert response.status_code == 401
    assert response.headers['www-authenticate'] == 'Bearer'
    mock_session.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_me_invalid_token(
    client: AsyncClient,
    mock_session,
):
    response = await client.get(
        '/api/v1/users/me',
        headers={'Authorization': 'Bearer invalid.token'},
    )

    assert response.status_code == 401
    mock_session.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_me_expired_token(
    client: AsyncClient,
    mock_session,
):
    token = create_access_token(
        subject='1',
        expires_delta=timedelta(minutes=-1),
    )

    response = await client.get(
        '/api/v1/users/me',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == 401
    mock_session.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_me_user_not_found(
    client: AsyncClient,
    mock_session,
):
    mock_user_query(mock_session, None)

    token = create_access_token(subject='999')

    response = await client.get(
        '/api/v1/users/me',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_inactive_user(
    client: AsyncClient,
    mock_session,
):
    user = make_user(is_active=False)
    mock_user_query(mock_session, user)

    token = create_access_token(subject=str(user.id))

    response = await client.get(
        '/api/v1/users/me',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == 403
    assert response.json()['detail'] == 'Usuário inativo'


@pytest.mark.asyncio
async def test_get_me_invalid_subject(
    client: AsyncClient,
    mock_session,
):
    settings = get_settings()

    token = jwt.encode(
        {
            'sub': 'invalid-id',
            'iat': datetime.now(UTC),
            'exp': datetime.now(UTC) + timedelta(minutes=30),
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    response = await client.get(
        '/api/v1/users/me',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == 401
    mock_session.execute.assert_not_awaited()

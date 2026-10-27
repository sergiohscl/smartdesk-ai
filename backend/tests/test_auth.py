from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from httpx import AsyncClient

from app.core.security import (
    decode_access_token,
    hash_password,
    verify_password,
)
from app.models.user import User


@pytest.mark.asyncio
async def test_register_user(
    client: AsyncClient,
    mock_session,
):
    result = MagicMock()
    result.scalar_one_or_none.return_value = None

    mock_session.execute.return_value = result

    async def fake_refresh(user):
        user.id = 1
        user.is_active = True
        user.created_at = datetime.now(UTC)
        user.updated_at = datetime.now(UTC)

    mock_session.refresh.side_effect = fake_refresh

    response = await client.post(
        '/api/v1/auth/register',
        json={
            'name': 'Usuario Teste',
            'email': 'usuario@teste.com',
            'password': 'SenhaSegura123',
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data['id'] == 1
    assert data['name'] == 'Usuario Teste'
    assert data['email'] == 'usuario@teste.com'
    assert data['is_active'] is True

    assert 'password' not in data
    assert 'hashed_password' not in data

    user = mock_session.add.call_args.args[0]

    assert user.hashed_password != 'SenhaSegura123'
    assert verify_password(
        'SenhaSegura123',
        user.hashed_password,
    )

    mock_session.commit.assert_awaited_once()


def make_user(
    password: str = 'SenhaSegura123',
    is_active: bool = True,
) -> User:
    return User(
        id=1,
        name='Usuario Teste',
        email='usuario@teste.com',
        hashed_password=hash_password(password),
        is_active=is_active,
    )


@pytest.mark.asyncio
async def test_login_success(
    client: AsyncClient,
    mock_session,
):
    user = make_user()

    result = MagicMock()
    result.scalar_one_or_none.return_value = user

    mock_session.execute.return_value = result

    response = await client.post(
        '/api/v1/auth/login',
        json={
            'email': 'usuario@teste.com',
            'password': 'SenhaSegura123',
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data['token_type'] == 'bearer'
    assert isinstance(data['access_token'], str)

    payload = decode_access_token(data['access_token'])

    assert payload['sub'] == str(user.id)
    assert payload['exp'] > payload['iat']


@pytest.mark.asyncio
async def test_login_wrong_password(
    client: AsyncClient,
    mock_session,
):
    user = make_user()

    result = MagicMock()
    result.scalar_one_or_none.return_value = user

    mock_session.execute.return_value = result

    response = await client.post(
        '/api/v1/auth/login',
        json={
            'email': 'usuario@teste.com',
            'password': 'SenhaErrada123',
        },
    )

    assert response.status_code == 401
    assert response.json()['detail'] == ('E-mail ou senha inválidos')
    assert response.headers['www-authenticate'] == 'Bearer'


@pytest.mark.asyncio
async def test_login_user_not_found(
    client: AsyncClient,
    mock_session,
):
    result = MagicMock()
    result.scalar_one_or_none.return_value = None

    mock_session.execute.return_value = result

    response = await client.post(
        '/api/v1/auth/login',
        json={
            'email': 'inexistente@teste.com',
            'password': 'SenhaSegura123',
        },
    )

    assert response.status_code == 401
    assert response.json()['detail'] == ('E-mail ou senha inválidos')
    assert response.headers['www-authenticate'] == 'Bearer'


@pytest.mark.asyncio
async def test_login_inactive_user(
    client: AsyncClient,
    mock_session,
):
    user = make_user(is_active=False)

    result = MagicMock()
    result.scalar_one_or_none.return_value = user

    mock_session.execute.return_value = result

    response = await client.post(
        '/api/v1/auth/login',
        json={
            'email': 'usuario@teste.com',
            'password': 'SenhaSegura123',
        },
    )

    assert response.status_code == 403
    assert response.json()['detail'] == 'Usuário inativo'


@pytest.mark.asyncio
async def test_login_invalid_email(
    client: AsyncClient,
    mock_session,
):
    response = await client.post(
        '/api/v1/auth/login',
        json={
            'email': 'email-invalido',
            'password': 'SenhaSegura123',
        },
    )

    assert response.status_code == 422

    mock_session.execute.assert_not_awaited()

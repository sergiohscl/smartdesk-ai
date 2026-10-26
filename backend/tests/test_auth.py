from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from httpx import AsyncClient

from app.core.security import verify_password


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

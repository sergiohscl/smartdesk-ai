import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.v1.chat_security import ChatSecureRoute
from app.main import app

BASE_URL = '/api/v1/chat'

CHAT_ENDPOINTS = [
    ('POST', '/conversations', {}),
    ('GET', '/conversations', None),
    ('GET', '/conversations/1', None),
    ('PATCH', '/conversations/1', {'title': 'Novo título'}),
    ('DELETE', '/conversations/1', None),
    ('GET', '/conversations/1/messages', None),
    ('GET', '/usage', None),
    (
        'POST',
        '/conversations/1/cancel',
        {
            'generation_id': '123e4567-e89b-12d3-a456-426614174000',
        },
    ),
    (
        'POST',
        '/conversations/1/messages',
        {'content': 'Teste de segurança'},
    ),
    (
        'POST',
        '/conversations/1/messages/1/regenerate',
        None,
    ),
]


@pytest.mark.parametrize(
    ('method', 'path', 'payload'),
    CHAT_ENDPOINTS,
)
async def test_chat_endpoint_requires_authentication(
    method,
    path,
    payload,
):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url='http://test',
    ) as client:
        response = await client.request(
            method,
            f'{BASE_URL}{path}',
            json=payload,
        )

    assert response.status_code == 401


async def test_chat_route_prevents_response_caching():
    test_app = FastAPI()
    test_app.router.route_class = ChatSecureRoute

    @test_app.get('/private')
    async def private_response():
        return {'content': 'Private response'}

    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url='http://test',
    ) as client:
        response = await client.get('/private')

    assert response.status_code == 200
    assert response.headers['cache-control'] == 'no-store'

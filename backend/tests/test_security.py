from datetime import timedelta

import jwt
import pytest

from app.core.security import (
    create_access_token,
    decode_access_token,
)


def test_create_access_token():
    token = create_access_token(subject='1')

    assert isinstance(token, str)
    assert len(token) > 0


def test_decode_valid_access_token():
    token = create_access_token(subject='123')

    payload = decode_access_token(token)

    assert payload['sub'] == '123'
    assert 'iat' in payload
    assert 'exp' in payload
    assert payload['exp'] > payload['iat']


def test_expired_access_token():
    token = create_access_token(
        subject='1',
        expires_delta=timedelta(minutes=-1),
    )

    with pytest.raises(
        ValueError,
        match='Invalid or expired access token',
    ):
        decode_access_token(token)


def test_invalid_signature():
    token = jwt.encode(
        {'sub': '1', 'exp': 9999999999, 'iat': 1700000000},
        'another-secret-key-with-at-least-32-bytes',
        algorithm='HS256',
    )

    with pytest.raises(
        ValueError,
        match='Invalid or expired access token',
    ):
        decode_access_token(token)


def test_malformed_access_token():
    with pytest.raises(
        ValueError,
        match='Invalid or expired access token',
    ):
        decode_access_token('invalid.jwt.token')

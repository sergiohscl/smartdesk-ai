from collections.abc import Awaitable, Callable
from typing import override

from fastapi import Request, Response
from fastapi.routing import APIRoute


class ChatSecureRoute(APIRoute):
    """Prevent caching of private chat responses."""

    @override
    def get_route_handler(
        self,
    ) -> Callable[[Request], Awaitable[Response]]:
        handler = super().get_route_handler()

        async def secure_handler(request: Request) -> Response:
            response = await handler(request)
            response.headers['Cache-Control'] = 'no-store'
            return response

        return secure_handler

from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Path,
    Query,
    Response,
    status,
)
from fastapi.responses import StreamingResponse

from app.api.v1.chat_http_errors import (
    CHAT_DOMAIN_ERRORS,
    chat_http_exception,
)
from app.api.v1.chat_sse import create_sse_response
from app.core.chat_dependencies import ChatServiceDep
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.chat import (
    ChatCancellationRequest,
    ChatCancellationResponse,
    ChatConversationCreate,
    ChatConversationListResponse,
    ChatConversationPublic,
    ChatConversationUpdate,
    ChatMessageCreate,
    ChatMessageListResponse,
    ChatUsageResponse,
)

router = APIRouter(
    prefix='/chat',
    tags=['Chat'],
)

CurrentUserDep = Annotated[
    User,
    Depends(get_current_user),
]

ConversationId = Annotated[
    int,
    Path(ge=1, le=2_147_483_647),
]

MessageId = Annotated[
    int,
    Path(ge=1, le=2_147_483_647),
]

Page = Annotated[
    int,
    Query(ge=1, le=2_147_483_647),
]

PageSize = Annotated[
    int,
    Query(ge=1, le=100),
]


@router.post(
    '/conversations',
    response_model=ChatConversationPublic,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation(
    data: ChatConversationCreate,
    current_user: CurrentUserDep,
    service: ChatServiceDep,
) -> ChatConversationPublic:
    """Create a conversation for the authenticated user."""

    try:
        return await service.create_conversation(
            user_id=current_user.id,
            data=data,
        )
    except CHAT_DOMAIN_ERRORS as error:
        raise chat_http_exception(error) from None


@router.get(
    '/conversations',
    response_model=ChatConversationListResponse,
)
async def list_conversations(
    current_user: CurrentUserDep,
    service: ChatServiceDep,
    page: Page = 1,
    page_size: PageSize = 20,
) -> ChatConversationListResponse:
    """List conversations owned by the authenticated user."""

    try:
        return await service.list_conversations(
            user_id=current_user.id,
            page=page,
            page_size=page_size,
        )
    except CHAT_DOMAIN_ERRORS as error:
        raise chat_http_exception(error) from None


@router.get(
    '/conversations/{conversation_id}',
    response_model=ChatConversationPublic,
)
async def get_conversation(
    conversation_id: ConversationId,
    current_user: CurrentUserDep,
    service: ChatServiceDep,
) -> ChatConversationPublic:
    """Retrieve a conversation owned by the authenticated user."""

    try:
        return await service.get_conversation(
            user_id=current_user.id,
            conversation_id=conversation_id,
        )
    except CHAT_DOMAIN_ERRORS as error:
        raise chat_http_exception(error) from None


@router.patch(
    '/conversations/{conversation_id}',
    response_model=ChatConversationPublic,
)
async def update_conversation(
    conversation_id: ConversationId,
    data: ChatConversationUpdate,
    current_user: CurrentUserDep,
    service: ChatServiceDep,
) -> ChatConversationPublic:
    """Rename a conversation owned by the authenticated user."""

    try:
        return await service.update_conversation(
            user_id=current_user.id,
            conversation_id=conversation_id,
            data=data,
        )
    except CHAT_DOMAIN_ERRORS as error:
        raise chat_http_exception(error) from None


@router.delete(
    '/conversations/{conversation_id}',
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_conversation(
    conversation_id: ConversationId,
    current_user: CurrentUserDep,
    service: ChatServiceDep,
) -> Response:
    """Delete an idle conversation owned by the authenticated user."""

    try:
        await service.delete_conversation(
            user_id=current_user.id,
            conversation_id=conversation_id,
        )
    except CHAT_DOMAIN_ERRORS as error:
        raise chat_http_exception(error) from None

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )


@router.get(
    '/conversations/{conversation_id}/messages',
    response_model=ChatMessageListResponse,
)
async def list_messages(
    conversation_id: ConversationId,
    current_user: CurrentUserDep,
    service: ChatServiceDep,
    page: Page = 1,
    page_size: PageSize = 50,
) -> ChatMessageListResponse:
    """List messages from a conversation owned by the current user."""

    try:
        return await service.list_messages(
            user_id=current_user.id,
            conversation_id=conversation_id,
            page=page,
            page_size=page_size,
        )
    except CHAT_DOMAIN_ERRORS as error:
        raise chat_http_exception(error) from None


@router.get(
    '/usage',
    response_model=ChatUsageResponse,
)
async def get_usage(
    current_user: CurrentUserDep,
    service: ChatServiceDep,
) -> ChatUsageResponse:
    """Retrieve daily usage for the authenticated user."""

    try:
        return await service.get_usage(
            user_id=current_user.id,
        )
    except CHAT_DOMAIN_ERRORS as error:
        raise chat_http_exception(error) from None


@router.post(
    '/conversations/{conversation_id}/cancel',
    response_model=ChatCancellationResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def cancel_generation(
    conversation_id: ConversationId,
    data: ChatCancellationRequest,
    current_user: CurrentUserDep,
    service: ChatServiceDep,
) -> ChatCancellationResponse:
    """Request cancellation of an owned active generation."""

    try:
        return await service.cancel_generation(
            user_id=current_user.id,
            conversation_id=conversation_id,
            data=data,
        )
    except CHAT_DOMAIN_ERRORS as error:
        raise chat_http_exception(error) from None


@router.post(
    '/conversations/{conversation_id}/messages',
    response_class=StreamingResponse,
    responses={
        200: {
            'description': 'Chat generation event stream.',
            'content': {
                'text/event-stream': {
                    'schema': {'type': 'string'},
                },
            },
        },
    },
)
async def send_message(
    conversation_id: ConversationId,
    data: ChatMessageCreate,
    current_user: CurrentUserDep,
    service: ChatServiceDep,
) -> StreamingResponse:
    """Send a message and stream the assistant response."""

    try:
        prepared = await service.prepare_generation(
            user_id=current_user.id,
            conversation_id=conversation_id,
            data=data,
        )
    except CHAT_DOMAIN_ERRORS as error:
        raise chat_http_exception(error) from None

    return create_sse_response(
        service.stream_generation(prepared),
        on_unstarted=lambda: service.abort_unstarted_generation(
            prepared,
        ),
    )


@router.post(
    '/conversations/{conversation_id}/messages/{message_id}/regenerate',
    response_class=StreamingResponse,
    responses={
        200: {
            'description': 'Chat regeneration event stream.',
            'content': {
                'text/event-stream': {
                    'schema': {'type': 'string'},
                },
            },
        },
    },
)
async def regenerate_message(
    conversation_id: ConversationId,
    message_id: MessageId,
    current_user: CurrentUserDep,
    service: ChatServiceDep,
) -> StreamingResponse:
    """Regenerate the latest eligible assistant response."""

    try:
        prepared = await service.prepare_regeneration(
            user_id=current_user.id,
            conversation_id=conversation_id,
            message_id=message_id,
        )
    except CHAT_DOMAIN_ERRORS as error:
        raise chat_http_exception(error) from None

    return create_sse_response(
        service.stream_generation(prepared),
        on_unstarted=lambda: service.abort_unstarted_generation(
            prepared,
        ),
    )

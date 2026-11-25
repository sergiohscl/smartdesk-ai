from enum import Enum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.models.chat_conversation import ChatGenerationStatus
from app.models.chat_message import (
    ChatMessageRole,
    ChatMessageStatus,
)


def validate_chat_title(value: str) -> str:
    if '\x00' in value:
        raise ValueError('Conversation title cannot contain null characters.')

    return value


ChatTitle = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=150,
        strict=True,
    ),
    AfterValidator(validate_chat_title),
]


class ChatConversationCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')

    title: ChatTitle | None = None


class ChatConversationUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')

    title: ChatTitle


class ChatConversationPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(gt=0, strict=True)
    title: ChatTitle
    generation_status: ChatGenerationStatus
    generation_id: UUID | None
    created_at: AwareDatetime
    updated_at: AwareDatetime

    @model_validator(mode='after')
    def validate_generation_state(self):
        if self.updated_at < self.created_at:
            raise ValueError('Updated at cannot precede created at.')

        if (
            self.generation_status == ChatGenerationStatus.IDLE
            and self.generation_id is not None
        ):
            raise ValueError('Idle conversations cannot have a generation ID.')

        if (
            self.generation_status == ChatGenerationStatus.GENERATING
            and self.generation_id is None
        ):
            raise ValueError(
                'Generating conversations require a generation ID.'
            )

        return self


class ChatConversationListResponse(BaseModel):
    items: list[ChatConversationPublic]
    total: int = Field(ge=0, strict=True)
    page: int = Field(ge=1, strict=True)
    page_size: int = Field(ge=1, le=100, strict=True)
    pages: int = Field(ge=0, strict=True)

    @model_validator(mode='after')
    def validate_pagination(self):
        expected_pages = (self.total + self.page_size - 1) // self.page_size

        if self.pages != expected_pages:
            raise ValueError('Invalid total number of pages.')

        remaining = max(
            0,
            self.total - (self.page - 1) * self.page_size,
        )

        max_items = min(self.page_size, remaining)

        if len(self.items) > max_items:
            raise ValueError('Too many items for the requested page.')

        return self


ChatContent = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=8000,
        strict=True,
    ),
]


class ChatMessageCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')

    content: ChatContent

    @field_validator('content')
    @classmethod
    def validate_content(cls, value: str) -> str:
        if '\x00' in value:
            raise ValueError('Message content cannot contain null characters.')

        return value


class ChatMessagePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(gt=0, strict=True)
    conversation_id: int = Field(gt=0, strict=True)
    role: ChatMessageRole
    content: str = Field(strict=True)
    status: ChatMessageStatus
    model: str | None = Field(max_length=100, strict=True)
    generation_id: UUID | None
    input_tokens: int | None = Field(ge=0, strict=True)
    output_tokens: int | None = Field(ge=0, strict=True)
    reply_to_message_id: int | None = Field(gt=0, strict=True)
    regenerated_from_id: int | None = Field(gt=0, strict=True)
    is_active: bool = Field(strict=True)
    created_at: AwareDatetime
    completed_at: AwareDatetime | None

    @model_validator(mode='after')
    def validate_message_state(self):
        if self.created_at.utcoffset() is None:
            raise ValueError('Created at must be timezone-aware.')

        if self.completed_at is not None:
            if self.completed_at.utcoffset() is None:
                raise ValueError('Completed at must be timezone-aware.')

            if self.completed_at < self.created_at:
                raise ValueError('Completed at cannot precede created at.')

        if self.status == ChatMessageStatus.PENDING:
            if self.completed_at is not None:
                raise ValueError(
                    'Pending messages cannot have completion time.'
                )
        elif self.completed_at is None:
            raise ValueError('Terminal messages require completion time.')

        if '\x00' in self.content:
            raise ValueError('Message content cannot contain null characters.')

        if self.reply_to_message_id == self.id:
            raise ValueError('A message cannot reply to itself.')

        if self.regenerated_from_id == self.id:
            raise ValueError('A message cannot regenerate itself.')

        if self.role == ChatMessageRole.USER:
            self.validate_user_message()
        else:
            self.validate_assistant_message()

        return self

    def validate_user_message(self) -> None:
        if self.status != ChatMessageStatus.COMPLETED:
            raise ValueError('User messages must be completed.')

        if not self.content.strip():
            raise ValueError('User message content cannot be empty.')

        if not self.is_active:
            raise ValueError('User messages must be active.')

        assistant_fields = (
            self.model,
            self.generation_id,
            self.input_tokens,
            self.output_tokens,
            self.reply_to_message_id,
            self.regenerated_from_id,
        )

        if any(value is not None for value in assistant_fields):
            raise ValueError(
                'User messages cannot contain assistant metadata.'
            )

    def validate_assistant_message(self) -> None:
        if self.model is None or not self.model.strip():
            raise ValueError('Assistant messages require a model.')

        if self.generation_id is None:
            raise ValueError('Assistant messages require a generation ID.')

        if self.reply_to_message_id is None:
            raise ValueError('Assistant messages require a reply reference.')

        if self.status == ChatMessageStatus.COMPLETED:
            if not self.content.strip():
                raise ValueError(
                    'Completed assistant messages require content.'
                )
        elif self.is_active:
            raise ValueError(
                'Only completed assistant messages can be active.'
            )


class ChatMessageListResponse(BaseModel):
    items: list[ChatMessagePublic]
    total: int = Field(ge=0, strict=True)
    page: int = Field(ge=1, strict=True)
    page_size: int = Field(ge=1, le=100, strict=True)
    pages: int = Field(ge=0, strict=True)

    @model_validator(mode='after')
    def validate_pagination(self):
        expected_pages = (self.total + self.page_size - 1) // self.page_size

        if self.pages != expected_pages:
            raise ValueError('Invalid total number of pages.')

        remaining = max(
            0,
            self.total - (self.page - 1) * self.page_size,
        )

        max_items = min(self.page_size, remaining)

        if len(self.items) > max_items:
            raise ValueError('Too many items for the requested page.')

        conversation_ids = {item.conversation_id for item in self.items}

        if len(conversation_ids) > 1:
            raise ValueError('Messages must belong to the same conversation.')

        message_ids = {item.id for item in self.items}

        if len(message_ids) != len(self.items):
            raise ValueError('Message IDs must be unique within a page.')

        return self


class ChatCancellationRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    generation_id: UUID


class ChatCancellationResponse(BaseModel):
    conversation_id: int = Field(gt=0, strict=True)
    generation_id: UUID
    cancellation_requested: Literal[True]

    @field_validator('cancellation_requested', mode='before')
    @classmethod
    def validate_cancellation_requested(cls, value: object) -> bool:
        if value is not True:
            raise ValueError('Cancellation requested must be true.')

        return True


class ChatUsageResponse(BaseModel):
    daily_limit: int = Field(gt=0, strict=True)
    used: int = Field(ge=0, strict=True)
    remaining: int = Field(ge=0, strict=True)
    input_tokens: int = Field(ge=0, strict=True)
    output_tokens: int = Field(ge=0, strict=True)
    resets_at: AwareDatetime

    @model_validator(mode='after')
    def validate_usage(self):
        expected_remaining = max(
            0,
            self.daily_limit - self.used,
        )

        if self.remaining != expected_remaining:
            raise ValueError('Invalid remaining daily quota.')

        if self.resets_at.utcoffset().total_seconds() != 0:
            raise ValueError('Quota reset time must be in UTC.')

        if any((
            self.resets_at.hour,
            self.resets_at.minute,
            self.resets_at.second,
            self.resets_at.microsecond,
        )):
            raise ValueError('Daily quota must reset at midnight UTC.')

        return self


class ChatStreamErrorCode(str, Enum):
    MODEL_NOT_FOUND = 'MODEL_NOT_FOUND'
    PROVIDER_REQUEST_ERROR = 'PROVIDER_REQUEST_ERROR'
    PROVIDER_UNAVAILABLE = 'PROVIDER_UNAVAILABLE'
    GENERATION_TIMEOUT = 'GENERATION_TIMEOUT'
    INVALID_PROVIDER_RESPONSE = 'INVALID_PROVIDER_RESPONSE'
    STREAM_INTERRUPTED = 'STREAM_INTERRUPTED'
    INTERNAL_ERROR = 'INTERNAL_ERROR'


class ChatStreamEventBase(BaseModel):
    model_config = ConfigDict(extra='forbid')

    conversation_id: int = Field(gt=0, strict=True)
    generation_id: UUID
    assistant_message_id: int = Field(gt=0, strict=True)


class ChatMessageCreatedEvent(ChatStreamEventBase):
    type: Literal['message.created']
    user_message_id: int = Field(gt=0, strict=True)
    regenerated_from_id: int | None = Field(
        default=None,
        gt=0,
        strict=True,
    )

    @model_validator(mode='after')
    def validate_message_ids(self):
        if self.user_message_id == self.assistant_message_id:
            raise ValueError('User and assistant message IDs must differ.')

        if self.regenerated_from_id in {
            self.user_message_id,
            self.assistant_message_id,
        }:
            raise ValueError('Invalid regenerated message reference.')

        return self


class ChatResponseDeltaEvent(ChatStreamEventBase):
    type: Literal['response.delta']
    delta: str = Field(min_length=1, strict=True)

    @field_validator('delta')
    @classmethod
    def validate_delta(cls, value: str) -> str:
        if '\x00' in value:
            raise ValueError('Delta cannot contain null characters.')

        return value


class ChatTerminalEventBase(ChatStreamEventBase):
    message: ChatMessagePublic

    @model_validator(mode='after')
    def validate_message_identity(self):
        if self.message.role != ChatMessageRole.ASSISTANT:
            raise ValueError('Terminal events require an assistant message.')

        if self.message.id != self.assistant_message_id:
            raise ValueError('Message ID mismatch.')

        if self.message.conversation_id != self.conversation_id:
            raise ValueError('Conversation ID mismatch.')

        if self.message.generation_id != self.generation_id:
            raise ValueError('Generation ID mismatch.')

        return self


class ChatResponseCompletedEvent(ChatTerminalEventBase):
    type: Literal['response.completed']

    @model_validator(mode='after')
    def validate_completed(self):
        if self.message.status != ChatMessageStatus.COMPLETED:
            raise ValueError('Expected completed message.')

        if not self.message.is_active:
            raise ValueError('Completed response must be active.')

        return self


class ChatResponseCancelledEvent(ChatTerminalEventBase):
    type: Literal['response.cancelled']

    @model_validator(mode='after')
    def validate_cancelled(self):
        if self.message.status != ChatMessageStatus.CANCELLED:
            raise ValueError('Expected cancelled message.')

        return self


class ChatResponseFailedEvent(ChatTerminalEventBase):
    type: Literal['response.failed']
    error_code: ChatStreamErrorCode

    @model_validator(mode='after')
    def validate_failed(self):
        if self.message.status != ChatMessageStatus.FAILED:
            raise ValueError('Expected failed message.')

        return self


class ChatResponseTruncatedEvent(ChatTerminalEventBase):
    type: Literal['response.truncated']

    @model_validator(mode='after')
    def validate_truncated(self):
        if self.message.status != ChatMessageStatus.TRUNCATED:
            raise ValueError('Expected truncated message.')

        return self


ChatStreamEvent = Annotated[
    ChatMessageCreatedEvent
    | ChatResponseDeltaEvent
    | ChatResponseCompletedEvent
    | ChatResponseCancelledEvent
    | ChatResponseFailedEvent
    | ChatResponseTruncatedEvent,
    Field(discriminator='type'),
]

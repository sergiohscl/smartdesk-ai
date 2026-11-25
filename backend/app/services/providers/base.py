from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass
from enum import StrEnum


class ProviderRole(StrEnum):
    SYSTEM = 'system'
    USER = 'user'
    ASSISTANT = 'assistant'


class ProviderFinishReason(StrEnum):
    STOP = 'stop'
    LENGTH = 'length'


@dataclass(frozen=True, slots=True)
class ProviderMessage:
    role: ProviderRole
    content: str

    def __post_init__(self) -> None:
        if not isinstance(self.role, ProviderRole):
            raise ValueError('Invalid provider message role.')

        if not isinstance(self.content, str):
            raise ValueError('Message content must be a string.')

        if not self.content.strip():
            raise ValueError('Message content cannot be empty.')

        if chr(0) in self.content:
            raise ValueError('Message content cannot contain null characters.')


@dataclass(frozen=True, slots=True)
class ProviderRequest:
    messages: tuple[ProviderMessage, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.messages, tuple):
            raise ValueError('Messages must be a tuple.')

        if not self.messages:
            raise ValueError('At least one message is required.')

        if not all(
            isinstance(message, ProviderMessage) for message in self.messages
        ):
            raise ValueError('Invalid provider message.')

        if self.messages[-1].role != ProviderRole.USER:
            raise ValueError('The last message must have the user role.')

        system_positions = [
            index
            for index, message in enumerate(self.messages)
            if message.role == ProviderRole.SYSTEM
        ]

        if system_positions and system_positions != [0]:
            raise ValueError(
                'Only the first message can have the system role.'
            )


@dataclass(frozen=True, slots=True)
class ProviderUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None

    def __post_init__(self) -> None:
        for value in (self.input_tokens, self.output_tokens):
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError('Token counts must be non-negative integers.')


@dataclass(frozen=True, slots=True)
class ProviderDelta:
    content: str

    def __post_init__(self) -> None:
        if not isinstance(self.content, str):
            raise ValueError('Delta content must be a string.')

        if not self.content:
            raise ValueError('Delta content cannot be empty.')

        if chr(0) in self.content:
            raise ValueError('Delta content cannot contain null characters.')


@dataclass(frozen=True, slots=True)
class ProviderCompletion:
    finish_reason: ProviderFinishReason
    usage: ProviderUsage

    def __post_init__(self) -> None:
        if not isinstance(
            self.finish_reason,
            ProviderFinishReason,
        ):
            raise ValueError('Invalid provider finish reason.')

        if not isinstance(self.usage, ProviderUsage):
            raise ValueError('Invalid provider usage.')


type ProviderEvent = ProviderDelta | ProviderCompletion


class AIProvider(ABC):
    """Abstract contract for asynchronous AI generation."""

    @property
    @abstractmethod
    def model(self) -> str:
        """Return the configured model identifier."""

    @abstractmethod
    def stream(
        self,
        request: ProviderRequest,
    ) -> AsyncIterator[ProviderEvent]:
        """Yield response deltas followed by one completion."""

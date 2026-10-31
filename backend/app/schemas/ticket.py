from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.ticket import TicketPriority, TicketStatus


class TicketCreate(BaseModel):
    title: str = Field(
        min_length=3,
        max_length=200,
    )
    description: str = Field(
        min_length=5,
    )
    priority: TicketPriority = TicketPriority.MEDIUM


class TicketUpdate(BaseModel):
    title: str | None = Field(
        default=None,
        min_length=3,
        max_length=200,
    )
    description: str | None = Field(
        default=None,
        min_length=5,
    )
    status: TicketStatus | None = None
    priority: TicketPriority | None = None


class TicketPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    status: TicketStatus
    priority: TicketPriority
    created_by_id: int
    created_at: datetime
    updated_at: datetime


class TicketListResponse(BaseModel):
    items: list[TicketPublic]
    total: int
    page: int
    page_size: int
    pages: int


class TicketStats(BaseModel):
    total: int
    open: int
    in_progress: int
    resolved: int

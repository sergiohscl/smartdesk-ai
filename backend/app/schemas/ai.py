from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.models.ticket import TicketPriority


class AITicketCategory(StrEnum):
    HARDWARE = 'hardware'
    SOFTWARE = 'software'
    NETWORK = 'network'
    ACCESS = 'access'
    OTHER = 'other'


class AIClassification(BaseModel):
    model_config = ConfigDict(extra='forbid')

    suggested_priority: TicketPriority
    suggested_category: AITicketCategory
    reason: str = Field(
        min_length=1,
        max_length=500,
    )


class AIAnalysisResponse(AIClassification):
    ticket_id: int = Field(gt=0)


class AIAnalysisHistoryItem(AIClassification):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(gt=0)
    ticket_id: int = Field(gt=0)
    priority_at_analysis: TicketPriority
    analyzed_by_id: int = Field(gt=0)
    created_at: datetime
    applied_at: datetime | None = None
    applied_by_id: int | None = Field(default=None, gt=0)


class AIAnalysisHistoryResponse(BaseModel):
    items: list[AIAnalysisHistoryItem]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    pages: int = Field(ge=0)


class AIAnalysisApplyResponse(BaseModel):
    analysis_id: int = Field(gt=0)
    ticket_id: int = Field(gt=0)
    previous_priority: TicketPriority
    applied_priority: TicketPriority
    applied_at: datetime
    applied_by_id: int = Field(gt=0)

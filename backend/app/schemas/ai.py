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

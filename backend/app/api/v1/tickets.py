from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.dependencies import get_current_user
from app.models.ticket import Ticket
from app.models.user import User
from app.schemas.ticket import (
    TicketCreate,
    TicketListResponse,
    TicketPublic,
)

router = APIRouter(
    prefix='/tickets',
    tags=['Tickets'],
)


@router.post(
    '',
    response_model=TicketPublic,
    status_code=status.HTTP_201_CREATED,
)
async def create_ticket(
    ticket_data: TicketCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Ticket:
    ticket = Ticket(
        title=ticket_data.title,
        description=ticket_data.description,
        priority=ticket_data.priority,
        created_by_id=current_user.id,
    )

    session.add(ticket)

    await session.commit()
    await session.refresh(ticket)

    return ticket


@router.get(
    '',
    response_model=TicketListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_tickets(
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 10,
    sort_by: Literal[
        'id',
        'title',
        'status',
        'priority',
        'created_at',
        'updated_at',
    ] = 'created_at',
    sort_order: Literal['asc', 'desc'] = 'desc',
) -> TicketListResponse:
    filters = Ticket.created_by_id == current_user.id

    # Total de chamados do usuário autenticado
    count_query = select(func.count()).select_from(Ticket).where(filters)

    total = await session.scalar(count_query)
    total = total or 0

    # Campos permitidos para ordenação
    sort_columns = {
        'id': Ticket.id,
        'title': Ticket.title,
        'status': Ticket.status,
        'priority': Ticket.priority,
        'created_at': Ticket.created_at,
        'updated_at': Ticket.updated_at,
    }

    sort_column = sort_columns[sort_by]

    if sort_order == 'asc':
        ordering = sort_column.asc()
    else:
        ordering = sort_column.desc()

    # Paginação
    offset = (page - 1) * page_size

    query = (
        select(Ticket)
        .where(filters)
        .order_by(ordering, Ticket.id.asc())
        .offset(offset)
        .limit(page_size)
    )

    result = await session.execute(query)
    tickets = result.scalars().all()

    # Converter modelos SQLAlchemy para schemas Pydantic
    ticket_items = [TicketPublic.model_validate(ticket) for ticket in tickets]

    # Total de páginas
    pages = (total + page_size - 1) // page_size

    return TicketListResponse(
        items=ticket_items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )

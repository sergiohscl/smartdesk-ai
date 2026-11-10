from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_dependencies import get_ai_service
from app.core.database import get_session
from app.core.dependencies import get_current_user
from app.models.ai_analysis import AIAnalysis
from app.models.ticket import Ticket, TicketPriority, TicketStatus
from app.models.user import User, UserRole
from app.schemas.ai import (
    AIAnalysisApplyResponse,
    AIAnalysisHistoryItem,
    AIAnalysisHistoryResponse,
    AIAnalysisResponse,
)
from app.schemas.ticket import (
    TicketCreate,
    TicketListResponse,
    TicketPublic,
    TicketStats,
    TicketUpdate,
)
from app.services.ai_service import AIService, AIServiceError

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
    status: TicketStatus | None = None,
    priority: TicketPriority | None = None,
    search: Annotated[
        str | None,
        Query(max_length=200),
    ] = None,
) -> TicketListResponse:
    # Todos os usuários autenticados podem consultar os chamados.
    # As permissões de edição e exclusão continuam restritas.
    filters = []

    if status is not None:
        filters.append(Ticket.status == status)

    if priority is not None:
        filters.append(Ticket.priority == priority)

    if search is not None:
        normalized_search = search.strip()

        if normalized_search:
            escaped_search = (
                normalized_search
                .replace('\\', '\\\\')
                .replace('%', '\\%')
                .replace('_', '\\_')
            )

            filters.append(
                Ticket.title.ilike(
                    f'%{escaped_search}%',
                    escape='\\',
                )
            )

    # Total de chamados visíveis para a função do usuário
    count_query = select(func.count()).select_from(Ticket).where(*filters)
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
        .where(*filters)
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


@router.get(
    '/stats',
    response_model=TicketStats,
    status_code=status.HTTP_200_OK,
)
async def get_ticket_stats(
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> TicketStats:
    statement = select(
        func.count(Ticket.id).label('total'),
        func
        .count(Ticket.id)
        .filter(Ticket.status == TicketStatus.OPEN)
        .label('open'),
        func
        .count(Ticket.id)
        .filter(Ticket.status == TicketStatus.IN_PROGRESS)
        .label('in_progress'),
        func
        .count(Ticket.id)
        .filter(Ticket.status == TicketStatus.RESOLVED)
        .label('resolved'),
    )

    result = await session.execute(statement)
    stats = result.one()

    return TicketStats(
        total=stats.total,
        open=stats.open,
        in_progress=stats.in_progress,
        resolved=stats.resolved,
    )


@router.get(
    '/{ticket_id}',
    response_model=TicketPublic,
    status_code=status.HTTP_200_OK,
)
async def get_ticket(
    ticket_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Ticket:
    # Todos os usuários autenticados e ativos podem
    # visualizar os detalhes de qualquer chamado.
    # A autenticação continua obrigatória.
    statement = select(Ticket).where(Ticket.id == ticket_id)

    result = await session.execute(statement)
    ticket = result.scalar_one_or_none()

    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Chamado não encontrado.',
        )

    return ticket


@router.patch(
    '/{ticket_id}',
    response_model=TicketPublic,
    status_code=status.HTTP_200_OK,
)
async def update_ticket(
    ticket_id: int,
    ticket_data: TicketUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Ticket:
    statement = select(Ticket).where(Ticket.id == ticket_id)

    # USER pode editar apenas os próprios chamados.
    # SUPPORT e ADMIN podem editar qualquer chamado.
    if current_user.role not in {UserRole.SUPPORT, UserRole.ADMIN}:
        statement = statement.where(Ticket.created_by_id == current_user.id)

    result = await session.execute(statement)
    ticket = result.scalar_one_or_none()

    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Chamado não encontrado.',
        )

    update_data = ticket_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(ticket, field, value)

    if update_data:
        await session.commit()
        await session.refresh(ticket)

    return ticket


@router.delete(
    '/{ticket_id}',
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_ticket(
    ticket_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    statement = select(Ticket).where(Ticket.id == ticket_id)

    # USER pode excluir apenas os próprios chamados.
    # SUPPORT e ADMIN podem excluir qualquer chamado.
    if current_user.role not in {UserRole.SUPPORT, UserRole.ADMIN}:
        statement = statement.where(Ticket.created_by_id == current_user.id)

    result = await session.execute(statement)

    ticket = result.scalar_one_or_none()

    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Chamado não encontrado.',
        )

    await session.delete(ticket)
    await session.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


async def get_ticket_for_ai_analysis(
    ticket_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Ticket:
    if ticket_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail='ID do chamado inválido.',
        )

    statement = select(Ticket).where(Ticket.id == ticket_id)

    result = await session.execute(statement)
    ticket = result.scalar_one_or_none()

    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Chamado não encontrado.',
        )

    # USER pode analisar apenas os próprios chamados.
    # SUPPORT e ADMIN podem analisar qualquer chamado.
    if (
        current_user.role not in {UserRole.SUPPORT, UserRole.ADMIN}
        and ticket.created_by_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Você não tem permissão para analisar este chamado.',
        )

    return ticket


@router.post(
    '/{ticket_id}/analyze',
    response_model=AIAnalysisResponse,
    status_code=status.HTTP_200_OK,
)
async def analyze_ticket(
    ticket: Annotated[
        Ticket,
        Depends(get_ticket_for_ai_analysis),
    ],
    ai_service: Annotated[
        AIService,
        Depends(get_ai_service),
    ],
    session: Annotated[
        AsyncSession,
        Depends(get_session),
    ],
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
) -> AIAnalysisResponse:
    try:
        classification = await ai_service.analyze_ticket(
            title=ticket.title,
            description=ticket.description,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail='Os dados do chamado não podem ser analisados.',
        ) from exc
    except AIServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='Serviço de análise com IA indisponível.',
        ) from exc

    analysis = AIAnalysis(
        ticket_id=ticket.id,
        suggested_priority=classification.suggested_priority,
        suggested_category=classification.suggested_category.value,
        reason=classification.reason,
        priority_at_analysis=ticket.priority,
        analyzed_by_id=current_user.id,
    )

    session.add(analysis)

    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    return AIAnalysisResponse(
        analysis_id=analysis.id,
        ticket_id=ticket.id,
        **classification.model_dump(),
    )


@router.get(
    '/{ticket_id}/analyses',
    response_model=AIAnalysisHistoryResponse,
    status_code=status.HTTP_200_OK,
)
async def get_ticket_ai_analyses(
    ticket_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 10,
) -> AIAnalysisHistoryResponse:
    if ticket_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail='ID do chamado inválido.',
        )

    # A consulta ao histórico segue a política de leitura:
    # qualquer usuário autenticado e ativo pode consultar
    # o histórico de um chamado existente.
    ticket_statement = select(Ticket.id).where(
        Ticket.id == ticket_id,
    )

    ticket_result = await session.execute(ticket_statement)

    if ticket_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Chamado não encontrado.',
        )

    # Contar as análises vinculadas ao chamado.
    count_statement = select(func.count(AIAnalysis.id)).where(
        AIAnalysis.ticket_id == ticket_id
    )

    total = await session.scalar(count_statement)
    total = total or 0

    # Paginar e ordenar da mais recente para a mais antiga.
    offset = (page - 1) * page_size

    history_statement = (
        select(AIAnalysis)
        .where(AIAnalysis.ticket_id == ticket_id)
        .order_by(
            AIAnalysis.created_at.desc(),
            AIAnalysis.id.desc(),
        )
        .offset(offset)
        .limit(page_size)
    )

    result = await session.execute(history_statement)
    analyses = result.scalars().all()

    items = [
        AIAnalysisHistoryItem.model_validate(analysis) for analysis in analyses
    ]

    pages = (total + page_size - 1) // page_size

    return AIAnalysisHistoryResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.post(
    '/{ticket_id}/analyses/{analysis_id}/apply',
    response_model=AIAnalysisApplyResponse,
    status_code=status.HTTP_200_OK,
)
async def apply_ai_analysis(
    ticket_id: int,
    analysis_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AIAnalysisApplyResponse:
    if ticket_id <= 0 or analysis_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail='ID do chamado ou da análise inválido.',
        )

    # Bloquear primeiro o chamado para serializar aplicações
    # concorrentes de diferentes análises do mesmo chamado.
    ticket_statement = (
        select(Ticket).where(Ticket.id == ticket_id).with_for_update()
    )

    # USER só pode modificar chamados próprios.
    # SUPPORT e ADMIN podem modificar qualquer chamado.
    if current_user.role not in {UserRole.SUPPORT, UserRole.ADMIN}:
        ticket_statement = ticket_statement.where(
            Ticket.created_by_id == current_user.id,
        )

    ticket_result = await session.execute(ticket_statement)
    ticket = ticket_result.scalar_one_or_none()

    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Chamado não encontrado.',
        )

    # Bloquear a análise depois do chamado.
    analysis_statement = (
        select(AIAnalysis)
        .where(
            AIAnalysis.id == analysis_id,
            AIAnalysis.ticket_id == ticket_id,
        )
        .with_for_update()
    )

    analysis_result = await session.execute(analysis_statement)
    analysis = analysis_result.scalar_one_or_none()

    if analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Análise não encontrada para este chamado.',
        )

    if analysis.applied_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Esta análise já foi aplicada.',
        )

    previous_priority = ticket.priority
    applied_at = datetime.now(UTC)

    ticket.priority = analysis.suggested_priority
    analysis.applied_at = applied_at
    analysis.applied_by_id = current_user.id

    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    return AIAnalysisApplyResponse(
        analysis_id=analysis.id,
        ticket_id=ticket.id,
        previous_priority=previous_priority,
        applied_priority=analysis.suggested_priority,
        applied_at=applied_at,
        applied_by_id=current_user.id,
    )

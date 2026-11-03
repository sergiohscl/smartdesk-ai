import argparse
import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.database import SessionLocal, engine
from app.models.ticket import Ticket, TicketPriority, TicketStatus
from app.models.user import User

TICKET_SCENARIOS = [
    ('Erro ao acessar o sistema', 'Usuário não consegue realizar login.'),
    (
        'Impressora não responde',
        'Impressora não recebe trabalhos de impressão.',
    ),
    ('Instalação de software', 'Solicitação de instalação de aplicativo.'),
    ('Servidor indisponível', 'Servidor principal não responde.'),
    ('VPN desconectando', 'Conexão VPN apresenta quedas frequentes.'),
    ('Senha expirada', 'Usuário precisa redefinir a senha de acesso.'),
    ('Computador lento', 'Estação de trabalho apresenta lentidão.'),
    ('Falha no Outlook', 'Cliente de e-mail não sincroniza mensagens.'),
    ('Erro no sistema ERP', 'Sistema ERP apresenta erro ao salvar dados.'),
    ('Monitor sem imagem', 'Monitor não apresenta sinal de vídeo.'),
    ('Wi-Fi instável', 'Rede sem fio apresenta desconexões.'),
    ('Acesso à pasta compartilhada', 'Usuário não acessa arquivos da rede.'),
    ('Backup não concluído', 'Rotina de backup apresentou falha.'),
    ('Antivírus desatualizado', 'Atualização do antivírus não foi concluída.'),
    ('Teclado com defeito', 'Teclas apresentam falhas intermitentes.'),
    ('Erro de certificado', 'Navegador informa certificado inválido.'),
    ('Sistema fora do ar', 'Aplicação corporativa está indisponível.'),
    ('Solicitação de acesso', 'Usuário solicita acesso a novo sistema.'),
    ('Falha no Teams', 'Aplicativo não conecta às reuniões.'),
    ('Problema no scanner', 'Digitalização de documentos não funciona.'),
]

STATUSES = [
    TicketStatus.OPEN,
    TicketStatus.IN_PROGRESS,
    TicketStatus.RESOLVED,
]

PRIORITIES = [
    TicketPriority.LOW,
    TicketPriority.MEDIUM,
    TicketPriority.HIGH,
    TicketPriority.CRITICAL,
]


async def seed_tickets(user_id: int, count: int) -> None:
    async with SessionLocal() as session:
        user = await session.get(User, user_id)

        if user is None:
            raise ValueError(f'Usuário com ID {user_id} não encontrado.')

        if not user.is_active:
            raise ValueError('O usuário informado está inativo.')

        existing = await session.scalars(
            select(Ticket.title).where(Ticket.created_by_id == user_id)
        )

        existing_titles = set(existing.all())

        now = datetime.now(timezone.utc)
        new_tickets = []

        for index in range(count):
            title, description = TICKET_SCENARIOS[
                index % len(TICKET_SCENARIOS)
            ]

            title = f'[SEED-{index + 1:03d}] {title}'

            if title in existing_titles:
                continue

            ticket = Ticket(
                title=title,
                description=description,
                status=STATUSES[index % len(STATUSES)],
                priority=PRIORITIES[index % len(PRIORITIES)],
                created_by_id=user_id,
                created_at=now - timedelta(days=index % 30),
            )

            new_tickets.append(ticket)

        session.add_all(new_tickets)

        await session.commit()

        print(
            f'{len(new_tickets)} chamados fictícios criados '
            f'para o usuário {user_id}.'
        )


async def run_seed(user_id: int, count: int) -> None:
    try:
        await seed_tickets(user_id, count)
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Popular chamados de desenvolvimento.'
    )

    parser.add_argument(
        '--user-id',
        type=int,
        required=True,
    )

    parser.add_argument(
        '--count',
        type=int,
        default=50,
    )

    parser.add_argument(
        '--confirm-dev',
        action='store_true',
        help='Confirma uso exclusivo em desenvolvimento.',
    )

    args = parser.parse_args()

    if not args.confirm_dev:
        parser.error('Informe --confirm-dev para continuar.')

    if args.user_id < 1 or not 1 <= args.count <= 100:
        parser.error('Informe um usuário válido e entre 1 e 100 chamados.')

    asyncio.run(run_seed(args.user_id, args.count))


if __name__ == '__main__':
    main()

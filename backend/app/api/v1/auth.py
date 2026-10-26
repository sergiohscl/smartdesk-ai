from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import UserCreate, UserPublic

router = APIRouter(
    prefix='/auth',
    tags=['Authentication'],
)


@router.post(
    '/register',
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    data: UserCreate,
    session: AsyncSession = Depends(get_session),
):
    email = str(data.email).lower()

    result = await session.execute(select(User).where(User.email == email))

    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='E-mail já cadastrado',
        )

    user = User(
        name=data.name,
        email=email,
        hashed_password=hash_password(data.password),
    )

    session.add(user)

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='E-mail já cadastrado',
        ) from None

    await session.refresh(user)

    return user

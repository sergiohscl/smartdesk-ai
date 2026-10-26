from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.user import (
    TokenResponse,
    UserCreate,
    UserLogin,
    UserPublic,
)

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


@router.post(
    '/login',
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
)
async def login(
    data: UserLogin,
    session: AsyncSession = Depends(get_session),
):
    email = str(data.email).lower()

    result = await session.execute(select(User).where(User.email == email))

    user = result.scalar_one_or_none()

    if user is None or not verify_password(
        data.password,
        user.hashed_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='E-mail ou senha inválidos',
            headers={'WWW-Authenticate': 'Bearer'},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Usuário inativo',
        )

    access_token = create_access_token(
        subject=str(user.id),
    )

    return TokenResponse(
        access_token=access_token,
        token_type='bearer',
    )

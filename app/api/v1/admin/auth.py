"""
Autenticacion del panel admin: login, refresh token.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from pydantic import BaseModel
from app.core.database import get_db
from app.core.security import verify_password, create_access_token
from app.models.user import User, UserRole
from app.models.tenant import Tenant

router = APIRouter(prefix="/auth", tags=["Admin - Auth"])


class Token(BaseModel):
    access_token: str
    token_type: str
    user_name: str
    user_role: str
    tenant_id: str


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Login con email y password. Retorna JWT."""
    result = await db.execute(
        select(User, Tenant).join(Tenant, User.tenant_id == Tenant.id).where(
            and_(
                User.email == form_data.username,
                User.is_active == True,
                User.role.in_([UserRole.ADMIN, UserRole.MANAGER, UserRole.SUPERVISOR]),
            )
        )
    )
    row = result.one_or_none()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
        )

    user, tenant = row

    if not user.password_hash or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
        )

    token = create_access_token({
        "sub": str(user.id),
        "tenant_id": str(user.tenant_id),
        "tenant_slug": tenant.slug,
        "role": user.role.value,
        "name": user.name,
    })

    return Token(
        access_token=token,
        token_type="bearer",
        user_name=user.name,
        user_role=user.role.value,
        tenant_id=str(user.tenant_id),
    )

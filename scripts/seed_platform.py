"""
Script de seed para crear el tenant de plataforma y el super-admin del SaaS.

Uso:
    python scripts/seed_platform.py
    python scripts/seed_platform.py --email superadmin@midominio.com --password MiClave123

Crea:
    - Tenant especial con slug='__platform__' (si no existe)
    - 1 usuario ADMIN perteneciente a ese tenant (super-admin de la plataforma)

El super-admin puede:
    - Hacer login en /api/v1/admin/auth/login
    - Acceder a todos los endpoints de /api/v1/platform/tenants/
    - Crear, suspender, reactivar y configurar tenants

IMPORTANTE:
    - Este script es idempotente: si el tenant __platform__ ya existe, solo
      actualiza la contraseña del super-admin existente.
    - Guardar las credenciales en un gestor de contraseñas. No hacer commit
      de este script con credenciales reales.
"""
import asyncio
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, and_

from app.core.config import settings
from app.core.security import hash_password
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.core.database import Base

# -----------------------------------------------------------------------
# Defaults (sobreescribir via argumentos de línea de comandos)
# -----------------------------------------------------------------------
DEFAULT_EMAIL    = "superadmin@salesagent.io"
DEFAULT_PASSWORD = "PlatformAdmin2026!"
DEFAULT_PHONE    = "+570000000000"


async def seed(email: str, password: str, phone: str) -> None:
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        async with db.begin():

            # ----------------------------------------------------------------
            # 1. Crear o recuperar el tenant __platform__
            # ----------------------------------------------------------------
            result = await db.execute(
                select(Tenant).where(Tenant.slug == "__platform__")
            )
            platform_tenant = result.scalar_one_or_none()

            if not platform_tenant:
                platform_tenant = Tenant(
                    name="Sales Agent Platform",
                    slug="__platform__",
                    nit=None,
                    is_active=True,
                    plan="enterprise",
                    agent_name="Platform Admin",
                    primary_color="#1E293B",
                    email_config={"management_emails": [], "from_name": None},
                    schedule_config={},
                )
                db.add(platform_tenant)
                await db.flush()
                print(f"✅ Tenant '__platform__' creado  (id: {platform_tenant.id})")
            else:
                print(f"ℹ️  Tenant '__platform__' ya existe (id: {platform_tenant.id})")

            # ----------------------------------------------------------------
            # 2. Crear o actualizar el super-admin
            # ----------------------------------------------------------------
            phone_normalized = "".join(filter(str.isdigit, phone))

            result = await db.execute(
                select(User).where(
                    and_(
                        User.tenant_id == platform_tenant.id,
                        User.role == UserRole.ADMIN,
                    )
                )
            )
            existing_admin = result.scalar_one_or_none()

            if existing_admin:
                existing_admin.email = email
                existing_admin.password_hash = hash_password(password)
                existing_admin.phone = phone
                existing_admin.phone_normalized = phone_normalized
                existing_admin.is_active = True
                print(f"🔄 Super-admin actualizado   (id: {existing_admin.id})")
                admin = existing_admin
            else:
                admin = User(
                    tenant_id=platform_tenant.id,
                    name="Super Admin",
                    email=email,
                    phone=phone,
                    phone_normalized=phone_normalized,
                    role=UserRole.ADMIN,
                    is_active=True,
                    password_hash=hash_password(password),
                    whatsapp_opt_in=False,
                )
                db.add(admin)
                await db.flush()
                print(f"✅ Super-admin creado         (id: {admin.id})")

    await engine.dispose()

    print()
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  CREDENCIALES DEL SUPER-ADMIN DE PLATAFORMA")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  URL login : POST /api/v1/admin/auth/login")
    print(f"  Email     : {email}")
    print(f"  Contraseña: {password}")
    print()
    print("  Endpoints disponibles tras login:")
    print("  GET    /api/v1/platform/tenants/")
    print("  POST   /api/v1/platform/tenants/")
    print("  GET    /api/v1/platform/tenants/{id}")
    print("  PATCH  /api/v1/platform/tenants/{id}")
    print("  POST   /api/v1/platform/tenants/{id}/suspend")
    print("  POST   /api/v1/platform/tenants/{id}/activate")
    print("  POST   /api/v1/platform/tenants/{id}/reset-token")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print()
    print("⚠️  Guardar estas credenciales en un gestor de contraseñas.")
    print("   No hacer commit de este script con contraseñas reales.")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed del tenant de plataforma y super-admin")
    parser.add_argument("--email",    default=DEFAULT_EMAIL,    help="Email del super-admin")
    parser.add_argument("--password", default=DEFAULT_PASSWORD, help="Contraseña del super-admin")
    parser.add_argument("--phone",    default=DEFAULT_PHONE,    help="Teléfono del super-admin")
    args = parser.parse_args()

    asyncio.run(seed(args.email, args.password, args.phone))


if __name__ == "__main__":
    main()

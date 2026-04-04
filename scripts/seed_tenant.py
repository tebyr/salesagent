"""
Script de seed para crear el primer tenant con datos de prueba.

Uso:
    python scripts/seed_tenant.py
    python scripts/seed_tenant.py --company "Distribuidora Demo" --email admin@demo.com

Crea:
    - 1 tenant
    - 1 usuario admin/gerente
    - 3 vendedores
    - 20 clientes distribuidos entre los vendedores
    - 15 productos de ejemplo
    - Metas mensuales para cada vendedor
"""
import asyncio
import argparse
import random
from datetime import date, timedelta

# Ajustar path para importar desde la raiz del proyecto
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.core.security import get_password_hash
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.models.client import Client
from app.models.product import Product
from app.models.goal import SalesGoal
from app.core.database import Base


# ------------------------------------------------------------------ #
# Datos de ejemplo
# ------------------------------------------------------------------ #

PRODUCTS = [
    ("Aceite Girasol 3L",        "aceites",      18500, False),
    ("Aceite Palma 1L",          "aceites",       8200, False),
    ("Arroz Diana 5Kg",          "granos",       22000, False),
    ("Arroz Roa 2Kg",            "granos",        9800, True),
    ("Azucar Riopaila 2Kg",      "azucar_sal",    7500, False),
    ("Sal Refisal 1Kg",          "azucar_sal",    2100, False),
    ("Frijol Cargamanto 500g",   "granos",        6800, True),
    ("Lenteja Verde 500g",       "granos",        5500, True),
    ("Pasta Doria Espagueti",    "pastas",        3200, False),
    ("Pasta Doria Codos",        "pastas",        3200, False),
    ("Jabon Rey x3",             "aseo",          8900, False),
    ("Detergente Ariel 1Kg",     "aseo",         14500, False),
    ("Suavizante Downy 850ml",   "aseo",         12800, True),
    ("Cafe Colcafe 150g",        "bebidas",       9500, False),
    ("Panela Redonda 1Kg",       "panela",        4200, False),
]

CLIENTS = [
    ("Tienda El Progreso", "Norte"),
    ("Minimercado La Esperanza", "Norte"),
    ("Tienda Dona Carmen", "Norte"),
    ("Granero El Buen Precio", "Norte"),
    ("Supermercado El Ahorro", "Norte"),
    ("Tienda La Esquina", "Centro"),
    ("Minimercado San Jose", "Centro"),
    ("Tienda El Paraiso", "Centro"),
    ("Granero El Exito", "Centro"),
    ("Tienda La Bendicion", "Centro"),
    ("Minimercado El Sol", "Sur"),
    ("Tienda Don Pedro", "Sur"),
    ("Granero La Cosecha", "Sur"),
    ("Tienda El Manantial", "Sur"),
    ("Minimercado La Union", "Sur"),
    ("Tienda El Milagro", "Oriente"),
    ("Granero Don Luis", "Oriente"),
    ("Tienda La Victoria", "Oriente"),
    ("Minimercado El Triunfo", "Oriente"),
    ("Tienda La Fortuna", "Oriente"),
]

VENDORS = [
    ("Carlos Mendez",   "3001111111", "Norte"),
    ("Sandra Gutierrez","3002222222", "Centro"),
    ("Juan Perez",      "3003333333", "Sur"),
]


async def seed(company: str, admin_email: str, admin_password: str):
    # Conexion directa con el motor async
    db_url = settings.database_url
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(db_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        print(f"\n🌱 Iniciando seed para tenant: {company}")

        # ---- Tenant ----
        slug = company.lower().replace(" ", "-").replace(".", "")[:50]
        tenant = Tenant(
            name=company,
            slug=slug,
            agent_name="VendorBot",
            primary_color="#2563EB",
            email_config={"management_emails": [admin_email], "from_name": company},
            schedule_config={
                "morning_briefing": "06:30",
                "pre_visit_start": "08:00",
                "pre_visit_end": "17:00",
                "daily_summary": "18:30",
                "performance_report": "20:00",
                "management_report_time": "07:00",
                "timezone": "America/Bogota",
            },
        )
        db.add(tenant)
        await db.flush()
        print(f"  ✅ Tenant creado: {tenant.name} (id={str(tenant.id)[:8]}...)")

        # ---- Admin/Gerente ----
        admin = User(
            tenant_id=tenant.id,
            name="Gerente General",
            phone="3009999999",
            email=admin_email,
            hashed_password=get_password_hash(admin_password),
            role=UserRole.MANAGER,
            is_active=True,
        )
        db.add(admin)
        await db.flush()
        print(f"  ✅ Admin creado: {admin_email} / {admin_password}")

        # ---- Vendedores ----
        salesperson_objects = []
        for name, phone, zone in VENDORS:
            salesperson = User(
                tenant_id=tenant.id,
                name=name,
                phone=phone,
                role=UserRole.VENDOR,
                zone=zone,
                is_active=True,
                whatsapp_opt_in=True,
            )
            db.add(salesperson)
            salesperson_objects.append(salesperson)
        await db.flush()
        print(f"  ✅ {len(salesperson_objects)} vendedores creados")

        # ---- Clientes ----
        segments = ["vip", "regular", "regular", "occasional"]
        for i, (name, zone) in enumerate(CLIENTS):
            assigned_vendor = salesperson_objects[i % len(salesperson_objects)]
            days_ago = random.randint(0, 60)
            client = Client(
                tenant_id=tenant.id,
                salesperson_id=assigned_vendor.id,
                name=name,
                phone=f"30{i+10:08d}",
                zone=zone,
                segment=random.choice(segments),
                is_active=True,
                whatsapp_opt_in=True,
                last_purchase_date=date.today() - timedelta(days=days_ago),
                purchase_frequency_days=random.choice([7, 14, 21, 30]),
                credit_limit=random.choice([500000, 1000000, 2000000, None]),
            )
            db.add(client)
        await db.flush()
        print(f"  ✅ {len(CLIENTS)} clientes creados")

        # ---- Productos ----
        product_objects = []
        for name, category, price, low_rotation in PRODUCTS:
            product = Product(
                tenant_id=tenant.id,
                name=name,
                category=category,
                price=float(price),
                unit="unidad",
                is_active=True,
                has_low_rotation=low_rotation,
            )
            db.add(product)
            product_objects.append(product)
        await db.flush()
        print(f"  ✅ {len(PRODUCTS)} productos creados")

        # ---- Metas del mes actual ----
        today = date.today()
        period_start = today.replace(day=1)
        if today.month == 12:
            period_end = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            period_end = today.replace(month=today.month + 1, day=1) - timedelta(days=1)

        goals_amounts = [8_000_000, 10_000_000, 7_000_000]
        for salesperson, amount in zip(salesperson_objects, goals_amounts):
            goal = SalesGoal(
                tenant_id=tenant.id,
                salesperson_id=salesperson.id,
                period_type="monthly",
                period_start=period_start,
                period_end=period_end,
                target_amount=float(amount),
                target_visits=20,
                is_active=True,
            )
            db.add(goal)
        await db.flush()
        print(f"  ✅ Metas mensuales creadas para {len(salesperson_objects)} vendedores")

        await db.commit()

    await engine.dispose()

    print(f"""
╔══════════════════════════════════════════════════════╗
║  Seed completado exitosamente                        ║
╠══════════════════════════════════════════════════════╣
║  Tenant  : {company:<42}║
║  Admin   : {admin_email:<42}║
║  Password: {admin_password:<42}║
║                                                      ║
║  Abre http://localhost:3000 y prueba el login        ║
╚══════════════════════════════════════════════════════╝
""")


def main():
    parser = argparse.ArgumentParser(description="Seed inicial del sistema")
    parser.add_argument("--company", default="Distribuidora Demo SAS",
                        help="Nombre de la empresa")
    parser.add_argument("--email", default="admin@demo.com",
                        help="Email del administrador")
    parser.add_argument("--password", default="Demo2026!",
                        help="Contraseña del administrador")
    args = parser.parse_args()

    asyncio.run(seed(args.company, args.email, args.password))


if __name__ == "__main__":
    main()

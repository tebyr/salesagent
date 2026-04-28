"""
Script de seed para crear el primer tenant con datos de prueba.

Uso:
    python scripts/seed_tenant.py
    python scripts/seed_tenant.py --company "Distribuciones La Garantia" --email admin@lagarantia.co

Crea:
    - 1 tenant (Distribuciones La Garantia, Magangue, Bolivar)
    - 1 usuario manager (gerente)
    - 3 vendedores de campo
    - 1 usuario AGENT (vendedor virtual IA)
    - 3 zonas geograficas: Norte, Centro, Sur
    - 6 rutas: 1 presencial + 1 agent_wa por zona
    - 40 clientes distribuidos entre las zonas
    - 30 productos con SKU, marca, categoria, subcategoria
    - Metas mensuales para cada vendedor
    - 90 dias de historial de pedidos (para calculo de afinidades)
"""
import asyncio
import argparse
import random
from datetime import date, timedelta
from decimal import Decimal

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.security import hash_password
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.models.client import Client
from app.models.product import Product
from app.models.goal import SalesGoal, GoalPeriodType
from app.models.route import Zone, Route, RouteType, RouteStatus
from app.models.order import Order, OrderItem, OrderStatus, OrderSource
from app.core.database import Base


# ------------------------------------------------------------------ #
# Datos de ejemplo — Distribuciones La Garantia, Magangue, Bolivar
# ------------------------------------------------------------------ #

# (sku, name, brand, category, subcategory, unit, unit_content, price, rotation_flag)
PRODUCTS = [
    # Aceites
    ("ACE-001", "Aceite de Girasol 3L",       "Girasol",    "aceites",     "girasol",     "Caja",    "6 unidades",    111_000, None),
    ("ACE-002", "Aceite de Palma 1L",          "La Buena",   "aceites",     "palma",       "Caja",    "12 unidades",    98_400, None),
    ("ACE-003", "Aceite Vegetal 500ml",        "Oleocali",   "aceites",     "vegetal",     "Caja",    "24 unidades",    96_000, "slow"),
    # Granos
    ("GRA-001", "Arroz Diana x 5Kg",           "Diana",      "granos",      "arroz",       "Bulto",   "10 bolsas",     220_000, None),
    ("GRA-002", "Arroz Roa x 2Kg",             "Roa",        "granos",      "arroz",       "Bulto",   "25 bolsas",     245_000, None),
    ("GRA-003", "Arroz 3 Castillos x 500g",    "3 Castillos","granos",      "arroz",       "Caja",    "24 bolsas",      96_000, "slow"),
    ("GRA-004", "Frijol Cargamanto 500g",      "La Rural",   "granos",      "frijol",      "Caja",    "20 bolsas",     136_000, "slow"),
    ("GRA-005", "Lenteja Verde 500g",           "La Rural",   "granos",      "lenteja",     "Caja",    "20 bolsas",     110_000, "slow"),
    ("GRA-006", "Maiz Trillado 1Kg",           "Doñarepa",   "granos",      "maiz",        "Bulto",   "20 bolsas",     160_000, "slow"),
    # Azucar y sal
    ("AZU-001", "Azucar Riopaila x 2Kg",       "Riopaila",   "azucar_sal",  "azucar",      "Bulto",   "20 bolsas",     150_000, None),
    ("AZU-002", "Azucar Manuelita x 1Kg",      "Manuelita",  "azucar_sal",  "azucar",      "Bulto",   "40 bolsas",     160_000, None),
    ("AZU-003", "Sal Refisal x 1Kg",            "Refisal",    "azucar_sal",  "sal",         "Bulto",   "25 bolsas",      52_500, None),
    # Pastas
    ("PAS-001", "Pasta Doria Espagueti x 250g","Doria",      "pastas",      "espagueti",   "Caja",    "24 unidades",    76_800, None),
    ("PAS-002", "Pasta Doria Codos x 250g",    "Doria",      "pastas",      "codos",       "Caja",    "24 unidades",    76_800, None),
    ("PAS-003", "Pasta La Muñeca Cabello",     "La Muñeca",  "pastas",      "cabello_angel","Caja",   "24 unidades",    67_200, "slow"),
    # Aseo
    ("ASE-001", "Jabon Rey x3 unidades",       "Rey",        "aseo",        "jabon_lavar", "Caja",    "12 paquetes",   106_800, None),
    ("ASE-002", "Detergente Ariel 1Kg",        "Ariel",      "aseo",        "detergente",  "Caja",    "12 unidades",   174_000, None),
    ("ASE-003", "Detergente Fab 500g",         "Fab",        "aseo",        "detergente",  "Caja",    "24 unidades",   120_000, "slow"),
    ("ASE-004", "Suavizante Downy 850ml",      "Downy",      "aseo",        "suavizante",  "Caja",    "12 unidades",   153_600, "slow"),
    ("ASE-005", "Esponjilla Scotch-Brite x3",  "Scotch-Brite","aseo",       "esponjilla",  "Caja",    "10 paquetes",    75_000, "slow"),
    # Bebidas y cafe
    ("BEB-001", "Cafe Colcafe Clasico 150g",   "Colcafe",    "bebidas",     "cafe",        "Caja",    "24 unidades",   228_000, None),
    ("BEB-002", "Cafe Sello Rojo 250g",        "Sello Rojo", "bebidas",     "cafe",        "Caja",    "24 unidades",   312_000, None),
    ("BEB-003", "Avena Alpina x 200ml",        "Alpina",     "bebidas",     "avena",       "Caja",    "30 unidades",   105_000, None),
    # Panela y endulzantes
    ("PAN-001", "Panela Redonda 1Kg",          "La Higuera", "panela",      "panela_solida","Bulto",  "20 unidades",    84_000, None),
    ("PAN-002", "Panela Pulverizada 500g",     "Dulcipon",   "panela",      "panela_pulv", "Caja",    "24 unidades",    96_000, "slow"),
    # Enlatados y conservas
    ("ENL-001", "Atun Van Camps en Aceite 170g","Van Camps", "enlatados",   "atun",        "Caja",    "48 latas",      240_000, None),
    ("ENL-002", "Sardinas Pampa 125g",         "Pampa",      "enlatados",   "sardinas",    "Caja",    "50 latas",      225_000, "slow"),
    ("ENL-003", "Tomate Frito La Viña 200g",   "La Viña",    "enlatados",   "tomate",      "Caja",    "24 unidades",    96_000, None),
    # Lacteos UHT
    ("LAC-001", "Leche Lala Entera 1L",        "Lala",       "lacteos",     "leche_uht",   "Caja",    "12 unidades",   108_000, None),
    ("LAC-002", "Leche Parmalat 1L",           "Parmalat",   "lacteos",     "leche_uht",   "Caja",    "12 unidades",   105_600, None),
]

# (business_name, owner_name, phone_suffix, city, address, segment, channel_type,
#  avg_purchase_freq_days, zone_key)
CLIENTS = [
    # ZONA NORTE (14 clientes)
    ("Tienda El Progreso",            "Luis Herrera",    "30101", "Magangue", "Cra 5 # 10-22",     "A", "tradicional", 7,  "Norte"),
    ("Minimercado La Esperanza",      "Maria Suarez",    "30102", "Magangue", "Cl 8 # 4-15",       "A", "minimercado", 14, "Norte"),
    ("Granero El Buen Precio",        "Pedro Alvarez",   "30103", "Magangue", "Cra 7 # 6-40",      "B", "tradicional", 14, "Norte"),
    ("Tienda Dona Carmen",            "Carmen Romero",   "30104", "Magangue", "Cl 12 # 2-8",       "B", "tradicional", 21, "Norte"),
    ("Supermercado El Ahorro Norte",  "Jorge Pedraza",   "30105", "Magangue", "Av Principal # 44", "A", "supermercado",14, "Norte"),
    ("Tienda San Miguel",             "Rosa Diaz",       "30106", "Magangue", "Cra 9 # 15-3",      "C", "tradicional", 21, "Norte"),
    ("Granero El Campo",              "Antonio Mora",    "30107", "Magangue", "Cl 6 # 8-20",       "B", "tradicional", 14, "Norte"),
    ("Tienda La Palma",               "Gladis Torres",   "30108", "Hatillo de Loba", "Cra 2 # 3-5","C", "tradicional", 30, "Norte"),
    ("Minimercado El Norte",          "Yeferson Gil",    "30109", "Hatillo de Loba", "Cl 4 # 1-10", "B", "minimercado", 14, "Norte"),
    ("Tienda El Muelle",              "Isidro Caro",     "30110", "Talaigua Nuevo", "Cra 1 # 5-8",  "C", "tradicional", 30, "Norte"),
    ("Granero La Abundancia Norte",   "Miriam Petro",    "30111", "Talaigua Nuevo", "Cl 3 # 4-12",  "B", "tradicional", 14, "Norte"),
    ("Tienda Don Aurelio",            "Aurelio Blandon", "30112", "San Fernando","Cra 3 # 2-7",    "C", "tradicional", 21, "Norte"),
    ("Minimercado La Costa",          "Sandra Florez",   "30113", "San Fernando","Cl 7 # 3-14",    "B", "minimercado", 14, "Norte"),
    ("Tienda El Caracoli",            "Edwin Mena",      "30114", "Magangue", "Cra 11 # 20-5",    "C", "tradicional", 30, "Norte"),
    # ZONA CENTRO (13 clientes)
    ("Tienda La Esquina Centro",      "Beatriz Luna",    "30201", "Magangue", "Cl 15 # 6-10",     "A", "tradicional", 7,  "Centro"),
    ("Minimercado San Jose",          "Hernando Ruiz",   "30202", "Magangue", "Cra 8 # 12-25",    "A", "minimercado", 14, "Centro"),
    ("Tienda El Paraiso",             "Amparo Castro",   "30203", "Magangue", "Cl 18 # 3-9",      "B", "tradicional", 14, "Centro"),
    ("Granero El Exito Centro",       "Ramiro Osorio",   "30204", "Magangue", "Cra 6 # 14-31",    "B", "tradicional", 14, "Centro"),
    ("Tienda La Bendicion",           "Claudia Pinto",   "30205", "Magangue", "Cl 20 # 5-17",     "C", "tradicional", 21, "Centro"),
    ("Supermercado Central",          "Mario Reyes",     "30206", "Magangue", "Av 3 # 16-40",     "A", "supermercado",14, "Centro"),
    ("Tienda San Nicolas",            "Nelly Vargas",    "30207", "Magangue", "Cra 4 # 17-8",     "C", "tradicional", 21, "Centro"),
    ("Minimercado El Centro",         "Luz Marina Soto", "30208", "Magangue", "Cl 22 # 7-13",     "B", "minimercado", 14, "Centro"),
    ("Tienda El Porvenir",            "Abel Mendez",     "30209", "Magangue", "Cra 3 # 21-6",     "C", "tradicional", 30, "Centro"),
    ("Granero La Economia",           "Doris Acosta",    "30210", "Magangue", "Cl 25 # 4-18",     "B", "tradicional", 21, "Centro"),
    ("Tienda Dona Petrona",           "Petrona Fuentes", "30211", "Magangue", "Cra 5 # 23-11",    "C", "tradicional", 30, "Centro"),
    ("Minimercado Bello Horizonte",   "Alberto Ceron",   "30212", "Magangue", "Cl 27 # 6-22",     "B", "minimercado", 14, "Centro"),
    ("Tienda El Rincon",              "Esperanza Leal",  "30213", "Magangue", "Cra 7 # 26-9",     "C", "tradicional", 30, "Centro"),
    # ZONA SUR (13 clientes)
    ("Minimercado El Sol",            "Hector Aguilar",  "30301", "Magangue", "Cra 10 # 30-5",    "A", "minimercado", 14, "Sur"),
    ("Tienda Don Pedro",              "Pedro Aragon",    "30302", "Magangue", "Cl 32 # 8-16",     "B", "tradicional", 14, "Sur"),
    ("Granero La Cosecha",            "Isabel Meza",     "30303", "Magangue", "Cra 12 # 28-20",   "A", "tradicional", 7,  "Sur"),
    ("Tienda El Manantial",           "Carlos Sierra",   "30304", "Magangue", "Cl 35 # 5-11",     "B", "tradicional", 14, "Sur"),
    ("Minimercado La Union",          "Patricia Lagos",  "30305", "Magangue", "Cra 9 # 33-8",     "B", "minimercado", 14, "Sur"),
    ("Tienda El Milagro Sur",         "Gonzalo Peña",    "30306", "Magangue", "Cl 38 # 3-7",      "C", "tradicional", 21, "Sur"),
    ("Granero Don Luis",              "Luis Angulo",     "30307", "Magangue", "Cra 11 # 36-14",   "B", "tradicional", 14, "Sur"),
    ("Tienda La Victoria",            "Victoria Salcedo","30308", "Magangue", "Cl 40 # 7-25",     "C", "tradicional", 21, "Sur"),
    ("Minimercado El Triunfo",        "Ramon Barrios",   "30309", "Magangue", "Cra 13 # 38-3",    "B", "minimercado", 14, "Sur"),
    ("Tienda La Fortuna",             "Fortuna Ospino",  "30310", "Magangue", "Cl 42 # 9-18",     "C", "tradicional", 30, "Sur"),
    ("Granero El Palmar",             "Edilson Melo",    "30311", "Magangue", "Cra 15 # 41-7",    "B", "tradicional", 21, "Sur"),
    ("Tienda Dona Rosalba",           "Rosalba Velez",   "30312", "Magangue", "Cl 44 # 6-12",     "C", "tradicional", 30, "Sur"),
    ("Minimercado El Futuro",         "Jairo Arias",     "30313", "Magangue", "Cra 14 # 43-10",   "B", "minimercado", 14, "Sur"),
]

# Zonas: (key, nombre, descripcion)
ZONES = [
    ("Norte",  "Zona Norte Magangue",   "Barrios y municipios al norte de Magangue"),
    ("Centro", "Zona Centro Magangue",  "Centro historico y comercial de Magangue"),
    ("Sur",    "Zona Sur Magangue",     "Barrios al sur y periferia sur de Magangue"),
]


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #

def normalize_phone(phone: str) -> str:
    """Retorna solo digitos del numero."""
    return "".join(c for c in phone if c.isdigit())


def month_range(year: int, month: int):
    """Retorna (period_start, period_end) para el mes dado."""
    start = date(year, month, 1)
    if month == 12:
        end = date(year, 12, 31)
    else:
        end = date(year, month + 1, 1) - timedelta(days=1)
    return start, end


# ------------------------------------------------------------------ #
# Seed principal
# ------------------------------------------------------------------ #

async def seed(company: str, admin_email: str, admin_password: str):
    db_url = settings.database_url
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(db_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        print(f"\n🌱  Iniciando seed — {company}")

        # ── Tenant ─────────────────────────────────────────────────────
        slug = company.lower().replace(" ", "-").replace(".", "").replace(",", "")[:50]
        tenant = Tenant(
            name=company,
            slug=slug,
            agent_name="AgenteGarantia",
            primary_color="#1D4ED8",
            email_config={
                "management_emails": [admin_email],
                "from_name": company,
                "from_email": "agente@lagarantia.co",
            },
            schedule_config={
                "morning_briefing": "06:30",
                "pre_visit_start": "08:00",
                "pre_visit_end": "17:00",
                "daily_summary": "18:30",
                "no_visit_followup": "19:00",
                "performance_report": "20:00",
                "management_report_time": "07:00",
                "timezone": "America/Bogota",
            },
        )
        db.add(tenant)
        await db.flush()
        print(f"  ✅  Tenant: {tenant.name}  (id={str(tenant.id)[:8]}…)")

        # ── Manager / Admin ────────────────────────────────────────────
        manager = User(
            tenant_id=tenant.id,
            name="Gerente General",
            phone="+573009999999",
            phone_normalized="573009999999",
            email=admin_email,
            password_hash=hash_password(admin_password),
            role=UserRole.MANAGER,
            is_active=True,
            whatsapp_opt_in=True,
        )
        db.add(manager)
        await db.flush()
        print(f"  ✅  Manager: {admin_email} / {admin_password}")

        # ── Agente IA (usuario virtual) ────────────────────────────────
        agent_user = User(
            tenant_id=tenant.id,
            name="Agente IA Garantia",
            phone="+573008880000",
            phone_normalized="573008880000",
            email="agente-ia@lagarantia.co",
            role=UserRole.AGENT,
            is_active=True,
            whatsapp_opt_in=False,
        )
        db.add(agent_user)
        await db.flush()
        print(f"  ✅  Agente IA creado")

        # ── Vendedores ─────────────────────────────────────────────────
        salespersons_data = [
            ("Oscar Gomez",      "+573174003589", "Norte"),
            ("Sandra Gutierrez", "+573002222222", "Centro"),
            ("Danilo Juvinao",   "+573162460168", "Sur"),
        ]
        salesperson_by_zone: dict[str, User] = {}
        salesperson_list = []
        for name, phone, zone_key in salespersons_data:
            sp = User(
                tenant_id=tenant.id,
                name=name,
                phone=phone,
                phone_normalized=normalize_phone(phone),
                role=UserRole.SALESPERSON,
                zone=zone_key,
                is_active=True,
                whatsapp_opt_in=True,
            )
            db.add(sp)
            salesperson_by_zone[zone_key] = sp
            salesperson_list.append(sp)
        await db.flush()
        print(f"  ✅  {len(salesperson_list)} vendedores creados")

        # ── Zonas ──────────────────────────────────────────────────────
        zone_by_key: dict[str, Zone] = {}
        for key, name, desc in ZONES:
            z = Zone(
                tenant_id=tenant.id,
                name=name,
                description=desc,
                is_active=True,
            )
            db.add(z)
            zone_by_key[key] = z
        await db.flush()
        print(f"  ✅  {len(ZONES)} zonas creadas")

        # ── Rutas ──────────────────────────────────────────────────────
        routes_created = 0
        for zone_key, zone_obj in zone_by_key.items():
            sp = salesperson_by_zone[zone_key]
            zone_name = zone_obj.name.replace("Zona ", "")  # "Norte Magangue"

            # Ruta presencial: Lun, Mie, Vie
            r_pres = Route(
                tenant_id=tenant.id,
                zone_id=zone_obj.id,
                salesperson_id=sp.id,
                name=f"Ruta {zone_name} - Presencial",
                route_type=RouteType.PRESENTIAL,
                operating_days=[1, 3, 5],
                delivery_days=[3, 5],
                daily_schedule={
                    "1": {"start": "07:30", "end": "16:00", "cutoff": "15:30"},
                    "3": {"start": "07:30", "end": "16:00", "cutoff": "15:30"},
                    "5": {"start": "07:30", "end": "14:00", "cutoff": "13:30"},
                },
                status=RouteStatus.PENDING,
                is_active=True,
                total_clients=0,
            )
            db.add(r_pres)

            # Ruta agente IA: Mar, Jue
            r_agent = Route(
                tenant_id=tenant.id,
                zone_id=zone_obj.id,
                salesperson_id=agent_user.id,
                name=f"Ruta {zone_name} - Agente IA",
                route_type=RouteType.AGENT_WA,
                operating_days=[2, 4],
                delivery_days=[4],
                daily_schedule={
                    "2": {"start": "08:00", "end": "17:00", "cutoff": "16:00"},
                    "4": {"start": "08:00", "end": "17:00", "cutoff": "16:00"},
                },
                status=RouteStatus.PENDING,
                is_active=True,
                total_clients=0,
            )
            db.add(r_agent)
            routes_created += 2
        await db.flush()
        print(f"  ✅  {routes_created} rutas creadas (2 por zona)")

        # ── Clientes ───────────────────────────────────────────────────
        client_list = []
        client_count_by_zone: dict[str, int] = {"Norte": 0, "Centro": 0, "Sur": 0}

        for idx, (biz, owner, phone_sfx, city, address, segment,
                  channel, freq_days, zone_key) in enumerate(CLIENTS):
            phone = f"+57{phone_sfx}00{idx:02d}"
            sp = salesperson_by_zone[zone_key]
            z = zone_by_key[zone_key]
            days_ago = random.randint(3, freq_days + 10)

            c = Client(
                tenant_id=tenant.id,
                salesperson_id=sp.id,
                zone_id=z.id,
                business_name=biz,
                owner_name=owner,
                phone=phone,
                phone_normalized=normalize_phone(phone),
                city=city,
                address=address,
                segment=segment,
                channel_type=channel,
                is_active=True,
                whatsapp_opt_in=True,
                avg_purchase_frequency_days=freq_days,
                last_purchase_date=date.today() - timedelta(days=days_ago),
                avg_ticket_amount=random.choice([150_000, 250_000, 400_000, 600_000, 1_000_000]),
                total_purchases_count=0,
                total_purchases_amount=0.0,
            )
            db.add(c)
            client_list.append((c, zone_key, sp))
            client_count_by_zone[zone_key] += 1
        await db.flush()
        print(f"  ✅  {len(client_list)} clientes creados  "
              f"(Norte={client_count_by_zone['Norte']}, "
              f"Centro={client_count_by_zone['Centro']}, "
              f"Sur={client_count_by_zone['Sur']})")

        # ── Productos ──────────────────────────────────────────────────
        product_list = []
        for (sku, name, brand, cat, subcat, unit, unit_content,
             price, rot_flag) in PRODUCTS:
            p = Product(
                tenant_id=tenant.id,
                sku=sku,
                name=name,
                brand=brand,
                category=cat,
                subcategory=subcat,
                unit=unit,
                unit_content=unit_content,
                price=float(price),
                is_active=True,
                is_featured=(rot_flag is None and random.random() < 0.2),
                rotation_flag=rot_flag,
            )
            db.add(p)
            product_list.append(p)
        await db.flush()
        print(f"  ✅  {len(product_list)} productos creados")

        # ── Metas mensuales — mes actual ───────────────────────────────
        today = date.today()
        period_start, period_end = month_range(today.year, today.month)

        goals_amounts = {
            salesperson_list[0].id: 12_000_000,  # Oscar Gomez — Norte
            salesperson_list[1].id: 14_000_000,  # Sandra Gutierrez — Centro
            salesperson_list[2].id: 10_000_000,  # Danilo Juvinao — Sur
        }
        for sp in salesperson_list:
            goal = SalesGoal(
                tenant_id=tenant.id,
                salesperson_id=sp.id,
                period_type=GoalPeriodType.MONTHLY,
                period_start=period_start,
                period_end=period_end,
                target_amount=float(goals_amounts[sp.id]),
                target_visits=80,
                target_effective_visits=60,
                is_active=True,
            )
            db.add(goal)
        await db.flush()
        print(f"  ✅  Metas mensuales creadas para {len(salesperson_list)} vendedores")

        # ── Historial de pedidos — 90 dias ─────────────────────────────
        # Para cada cliente, crear pedidos segun su frecuencia de compra.
        # Cada pedido incluye 2-5 productos aleatorios.
        rng = random.Random(42)  # seed fija para reproducibilidad
        orders_total = 0
        items_total = 0

        for client_obj, zone_key, sp in client_list:
            freq = client_obj.avg_purchase_frequency_days or 14
            # Generar fechas de compra hacia atras desde hoy
            order_date = today - timedelta(days=rng.randint(2, freq))
            total_amount_accum = 0.0
            purchase_count = 0

            while order_date >= today - timedelta(days=90):
                # Seleccionar 2-5 productos
                num_items = rng.randint(2, 5)
                chosen_products = rng.sample(product_list, num_items)

                subtotal = 0.0
                order_items_data = []
                for prod in chosen_products:
                    qty = float(rng.randint(1, 4))
                    unit_price = prod.price
                    total_price = qty * unit_price
                    subtotal += total_price
                    order_items_data.append((prod, qty, unit_price, total_price))

                order_number = f"ORD-{str(tenant.id)[:4].upper()}-{orders_total + 1:05d}"
                order = Order(
                    tenant_id=tenant.id,
                    client_id=client_obj.id,
                    salesperson_id=sp.id,
                    order_number=order_number,
                    order_date=order_date,
                    delivery_date=order_date + timedelta(days=rng.randint(1, 3)),
                    status=OrderStatus.DELIVERED,
                    source=OrderSource.SALESPERSON,
                    subtotal=subtotal,
                    discount_amount=0.0,
                    total_amount=subtotal,
                )
                db.add(order)
                await db.flush()

                for prod, qty, unit_price, total_price in order_items_data:
                    item = OrderItem(
                        tenant_id=tenant.id,
                        order_id=order.id,
                        product_id=prod.id,
                        quantity=qty,
                        unit_price=unit_price,
                        discount_percent=0.0,
                        total_price=total_price,
                    )
                    db.add(item)
                    items_total += 1

                total_amount_accum += subtotal
                purchase_count += 1
                orders_total += 1

                # Siguiente compra hacia atras
                order_date = order_date - timedelta(days=rng.randint(
                    max(1, freq - 5), freq + 7
                ))

            # Actualizar contadores del cliente
            client_obj.total_purchases_count = purchase_count
            client_obj.total_purchases_amount = total_amount_accum

        await db.flush()
        print(f"  ✅  {orders_total} pedidos y {items_total} items creados (90 dias de historia)")

        await db.commit()

    await engine.dispose()

    print(f"""
╔══════════════════════════════════════════════════════════════╗
║  Seed completado exitosamente                                ║
╠══════════════════════════════════════════════════════════════╣
║  Tenant   : {company:<48}║
║  Admin    : {admin_email:<48}║
║  Password : {admin_password:<48}║
╠══════════════════════════════════════════════════════════════╣
║  Zonas    : 3  (Norte, Centro, Sur)                          ║
║  Rutas    : 6  (2 por zona: Presencial + Agente IA)          ║
║  Vendedores: 3 + 1 Agente IA                                 ║
║  Clientes : 40                                               ║
║  Productos: 30                                               ║
╠══════════════════════════════════════════════════════════════╣
║  Abre http://localhost:3000 para el panel admin              ║
╚══════════════════════════════════════════════════════════════╝
""")


def main():
    parser = argparse.ArgumentParser(description="Seed inicial del sistema")
    parser.add_argument(
        "--company", default="Distribuciones La Garantia",
        help="Nombre de la empresa",
    )
    parser.add_argument(
        "--email", default="admin@lagarantia.co",
        help="Email del administrador",
    )
    parser.add_argument(
        "--password", default="Garantia2026!",
        help="Contrasena del administrador",
    )
    args = parser.parse_args()

    asyncio.run(seed(args.company, args.email, args.password))


if __name__ == "__main__":
    main()

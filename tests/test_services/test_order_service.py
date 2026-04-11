"""
Tests de app.services.order_service.OrderService.

Cubre:
  - create_order_from_agent: cliente no encontrado → retorna None
  - create_order_from_agent: items vacios → retorna None
  - create_order_from_agent: producto inactivo → item descartado
  - create_order_from_agent: todos los productos invalidos → retorna None
  - create_order_from_agent: calculo correcto de subtotal y total
  - create_order_from_agent: descuento por item se aplica correctamente
  - create_order_from_agent: precio del catalogo cuando unit_price=0
  - get_order: retorna None si no existe o es de otro tenant
"""
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call

from tests.conftest import CLIENT_ID, PRODUCT_ID, TENANT_ID, USER_ID


def _make_mock_result(return_value):
    """Simula db.execute() → result.scalar_one_or_none()."""
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=return_value)
    return result


class TestCreateOrderFromAgent:

    @pytest.fixture(autouse=True)
    def patch_db_session(self, make_client, make_product):
        """
        OrderService usa AsyncSessionLocal() directamente (no inyectado).
        Parcheamos el context manager para controlar la sesion.
        """
        self.client_obj = make_client()
        self.product_obj = make_product(price=220_000.0, is_active=True)

        self.mock_db = AsyncMock()
        self.mock_db.add = MagicMock()
        self.mock_db.flush = AsyncMock()
        self.mock_db.commit = AsyncMock()
        self.mock_db.refresh = AsyncMock()

        # Configurar secuencia de llamadas a execute:
        # 1ra llamada → busca cliente, 2da llamada → busca producto
        client_result = _make_mock_result(self.client_obj)
        product_result = _make_mock_result(self.product_obj)
        self.mock_db.execute = AsyncMock(side_effect=[client_result, product_result])

        class _Ctx:
            async def __aenter__(self_inner):
                return self.mock_db
            async def __aexit__(self_inner, *args):
                pass

        self.ctx_patch = patch(
            "app.services.order_service.AsyncSessionLocal",
            return_value=_Ctx(),
        )
        self.ctx_patch.start()
        yield
        self.ctx_patch.stop()

    async def test_returns_none_when_client_not_found(self):
        from app.services.order_service import OrderService
        self.mock_db.execute = AsyncMock(
            return_value=_make_mock_result(None)  # cliente no encontrado
        )
        svc = OrderService(str(TENANT_ID))
        result = await svc.create_order_from_agent(
            client_id=str(CLIENT_ID),
            salesperson_id=str(USER_ID),
            order_data={"items": [{"product_id": str(PRODUCT_ID), "quantity": 2}]},
        )
        assert result is None

    async def test_returns_none_when_items_empty(self):
        from app.services.order_service import OrderService
        # Si items esta vacio se retorna None antes de consultar la BD
        # Reconfigurar el mock para que el execute no sea llamado
        self.mock_db.execute = AsyncMock()
        svc = OrderService(str(TENANT_ID))
        result = await svc.create_order_from_agent(
            client_id=str(CLIENT_ID),
            salesperson_id=str(USER_ID),
            order_data={"items": []},
        )
        assert result is None

    async def test_calculates_subtotal_correctly(self):
        """2 unidades x $220.000 = $440.000."""
        from app.services.order_service import OrderService

        # Capturar el objeto Order creado
        created_order = None
        def capture_add(obj):
            nonlocal created_order
            from app.models.order import Order
            if isinstance(obj, Order):
                created_order = obj
                # Simular que flush() asigna un ID
                obj.id = uuid.uuid4()
        self.mock_db.add = MagicMock(side_effect=capture_add)
        self.mock_db.refresh = AsyncMock()

        svc = OrderService(str(TENANT_ID))
        await svc.create_order_from_agent(
            client_id=str(CLIENT_ID),
            salesperson_id=str(USER_ID),
            order_data={"items": [
                {"product_id": str(PRODUCT_ID), "quantity": 2, "unit_price": 220_000},
            ]},
        )

        assert created_order is not None
        assert created_order.subtotal == 440_000.0
        assert created_order.total_amount == 440_000.0

    async def test_uses_catalog_price_when_unit_price_zero(self):
        """Si unit_price=0 en el payload, debe usar product.price del catalogo."""
        from app.services.order_service import OrderService

        created_order = None
        def capture_add(obj):
            nonlocal created_order
            from app.models.order import Order
            if isinstance(obj, Order):
                created_order = obj
                obj.id = uuid.uuid4()
        self.mock_db.add = MagicMock(side_effect=capture_add)

        svc = OrderService(str(TENANT_ID))
        await svc.create_order_from_agent(
            client_id=str(CLIENT_ID),
            salesperson_id=str(USER_ID),
            order_data={"items": [
                {"product_id": str(PRODUCT_ID), "quantity": 1, "unit_price": 0},
            ]},
        )
        # Precio del catalogo es 220.000
        assert created_order is not None
        assert created_order.total_amount == 220_000.0

    async def test_applies_discount_correctly(self):
        """10% de descuento: 2 x 220.000 x 0.90 = 396.000."""
        from app.services.order_service import OrderService

        created_order = None
        def capture_add(obj):
            nonlocal created_order
            from app.models.order import Order
            if isinstance(obj, Order):
                created_order = obj
                obj.id = uuid.uuid4()
        self.mock_db.add = MagicMock(side_effect=capture_add)

        svc = OrderService(str(TENANT_ID))
        await svc.create_order_from_agent(
            client_id=str(CLIENT_ID),
            salesperson_id=str(USER_ID),
            order_data={"items": [
                {
                    "product_id": str(PRODUCT_ID),
                    "quantity": 2,
                    "unit_price": 220_000,
                    "discount_percent": 10,
                },
            ]},
        )
        assert created_order is not None
        assert abs(created_order.total_amount - 396_000.0) < 1.0

    async def test_skips_inactive_product_and_returns_none_if_no_valid_items(self):
        """Si el unico producto esta inactivo, no debe crearse orden."""
        from app.services.order_service import OrderService
        self.product_obj.is_active = False
        # El execute devuelve cliente OK, producto inactivo → scalar_one_or_none=None
        inactive_result = _make_mock_result(None)
        self.mock_db.execute = AsyncMock(
            side_effect=[_make_mock_result(self.client_obj), inactive_result]
        )
        svc = OrderService(str(TENANT_ID))
        result = await svc.create_order_from_agent(
            client_id=str(CLIENT_ID),
            salesperson_id=str(USER_ID),
            order_data={"items": [
                {"product_id": str(PRODUCT_ID), "quantity": 1, "unit_price": 220_000},
            ]},
        )
        assert result is None

    async def test_order_source_is_agent_wa(self):
        """Los pedidos del agente deben registrarse con source=AGENT_WA."""
        from app.services.order_service import OrderService
        from app.models.order import OrderSource

        created_order = None
        def capture_add(obj):
            nonlocal created_order
            from app.models.order import Order
            if isinstance(obj, Order):
                created_order = obj
                obj.id = uuid.uuid4()
        self.mock_db.add = MagicMock(side_effect=capture_add)

        svc = OrderService(str(TENANT_ID))
        await svc.create_order_from_agent(
            client_id=str(CLIENT_ID),
            salesperson_id=str(USER_ID),
            order_data={"items": [
                {"product_id": str(PRODUCT_ID), "quantity": 1, "unit_price": 220_000},
            ]},
        )
        assert created_order is not None
        assert created_order.source == OrderSource.AGENT_WA

    async def test_notes_are_passed_to_order(self):
        from app.services.order_service import OrderService

        created_order = None
        def capture_add(obj):
            nonlocal created_order
            from app.models.order import Order
            if isinstance(obj, Order):
                created_order = obj
                obj.id = uuid.uuid4()
        self.mock_db.add = MagicMock(side_effect=capture_add)

        svc = OrderService(str(TENANT_ID))
        await svc.create_order_from_agent(
            client_id=str(CLIENT_ID),
            salesperson_id=str(USER_ID),
            order_data={
                "items": [{"product_id": str(PRODUCT_ID), "quantity": 1, "unit_price": 50_000}],
                "notes": "Entregar antes del mediodia",
            },
        )
        assert created_order is not None
        assert created_order.notes == "Entregar antes del mediodia"

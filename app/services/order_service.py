"""
OrderService — creacion y gestion de pedidos.

Crea pedidos originados en el agente (via WhatsApp) y desde el panel admin.
"""
from datetime import date
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.order import Order, OrderItem, OrderStatus, OrderSource
from app.models.product import Product
from app.models.client import Client
import structlog

logger = structlog.get_logger()


class OrderService:

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id

    async def create_order_from_agent(
        self,
        client_id: str,
        salesperson_id: str | None,
        order_data: dict,
    ) -> Order | None:
        """
        Crea un pedido a partir de los datos recopilados por el agente via WhatsApp.

        order_data esperado (viene del tool use del ClientAgent):
        {
            "items": [
                {"product_id": "uuid", "quantity": 2, "unit_price": 15000},
                ...
            ],
            "notes": "texto opcional"
        }
        """
        items_data = order_data.get("items", [])
        if not items_data:
            logger.warning("order_from_agent_empty_items", client_id=client_id)
            return None

        async with AsyncSessionLocal() as db:
            # Verificar que el cliente pertenece al tenant
            client_result = await db.execute(
                select(Client).where(
                    Client.id == client_id,
                    Client.tenant_id == self.tenant_id,
                )
            )
            client = client_result.scalar_one_or_none()
            if not client:
                logger.error("order_client_not_found", client_id=client_id)
                return None

            # Calcular totales
            subtotal = 0.0
            order_items = []

            for item_data in items_data:
                product_id = item_data.get("product_id")
                quantity = float(item_data.get("quantity", 1))
                unit_price = float(item_data.get("unit_price", 0))

                # Validar producto
                product_result = await db.execute(
                    select(Product).where(
                        Product.id == product_id,
                        Product.tenant_id == self.tenant_id,
                        Product.is_active == True,
                    )
                )
                product = product_result.scalar_one_or_none()

                if not product:
                    logger.warning("order_product_not_found", product_id=product_id)
                    continue

                # Usar precio del catalogo si no viene en el payload
                if unit_price == 0:
                    unit_price = product.price or 0.0

                discount_pct = float(item_data.get("discount_percent", 0))
                total_price = quantity * unit_price * (1 - discount_pct / 100)
                subtotal += total_price

                order_items.append(OrderItem(
                    tenant_id=self.tenant_id,
                    product_id=product_id,
                    quantity=quantity,
                    unit_price=unit_price,
                    discount_percent=discount_pct,
                    total_price=total_price,
                ))

            if not order_items:
                logger.error("order_no_valid_items", client_id=client_id)
                return None

            # Crear la orden
            order = Order(
                tenant_id=self.tenant_id,
                client_id=client_id,
                salesperson_id=salesperson_id,
                order_date=date.today(),
                status=OrderStatus.PENDING,
                source=OrderSource.AGENT_WA,
                subtotal=subtotal,
                discount_amount=0.0,
                total_amount=subtotal,
                notes=order_data.get("notes"),
            )
            db.add(order)
            await db.flush()  # Para obtener order.id

            for item in order_items:
                item.order_id = order.id
                db.add(item)

            await db.commit()
            await db.refresh(order)

            logger.info(
                "order_created",
                tenant_id=self.tenant_id,
                order_id=str(order.id),
                client_id=client_id,
                items=len(order_items),
                total=order.total_amount,
                source="agent_wa",
            )
            return order

    async def get_order(self, order_id: str) -> Order | None:
        """Obtiene un pedido por ID verificando que pertenezca al tenant."""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Order).where(
                    Order.id == order_id,
                    Order.tenant_id == self.tenant_id,
                )
            )
            return result.scalar_one_or_none()

    async def confirm_order(self, order_id: str) -> Order | None:
        """Confirma un pedido que estaba en estado PENDING."""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Order).where(
                    Order.id == order_id,
                    Order.tenant_id == self.tenant_id,
                )
            )
            order = result.scalar_one_or_none()
            if order and order.status == OrderStatus.PENDING:
                order.status = OrderStatus.CONFIRMED
                await db.commit()
                await db.refresh(order)
            return order

    async def cancel_order(self, order_id: str) -> Order | None:
        """Cancela un pedido."""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Order).where(
                    Order.id == order_id,
                    Order.tenant_id == self.tenant_id,
                )
            )
            order = result.scalar_one_or_none()
            if order and order.status in (OrderStatus.PENDING, OrderStatus.DRAFT):
                order.status = OrderStatus.CANCELLED
                await db.commit()
                await db.refresh(order)
            return order

    async def format_order_summary(self, order: Order) -> str:
        """
        Genera un resumen legible del pedido para enviar por WhatsApp.
        """
        async with AsyncSessionLocal() as db:
            # Cargar items con productos
            from sqlalchemy.orm import selectinload
            result = await db.execute(
                select(Order)
                .options(selectinload(Order.items).selectinload(OrderItem.product))
                .where(Order.id == order.id)
            )
            order_loaded = result.scalar_one_or_none()

        if not order_loaded:
            return "Pedido no encontrado."

        lines = [f"📦 *Pedido #{str(order.id)[:8].upper()}*\n"]
        for item in order_loaded.items:
            product_name = item.product.name if item.product else "Producto"
            lines.append(
                f"• {product_name}: {item.quantity:.0f} x "
                f"${item.unit_price:,.0f} = ${item.total_price:,.0f}"
            )

        lines.append(f"\n*Total: ${order.total_amount:,.0f} COP*")
        if order.notes:
            lines.append(f"_Nota: {order.notes}_")

        return "\n".join(lines)

"""
Productos del catalogo y promociones activas.
"""
from sqlalchemy import Column, String, Boolean, ForeignKey, Float, Integer, Date, Text, JSON, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.core.database import Base
from app.models.base import UUIDMixin, TimestampMixin


class Product(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("tenant_id", "external_id", name="uq_products_tenant_external_id"),
    )

    tenant_id = Column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)

    # Identificacion
    sku = Column(String(50), nullable=False, index=True)
    name = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    brand = Column(String(100), nullable=True)
    category = Column(String(100), nullable=False, index=True)
    subcategory = Column(String(100), nullable=True)

    # Presentacion
    unit = Column(String(50), nullable=True)    # caja, unidad, bolsa, etc.
    unit_content = Column(String(50), nullable=True)  # 12 unidades, 500g, etc.

    # Precios en COP
    price = Column(Float, nullable=False)
    price_promo = Column(Float, nullable=True)  # Precio promocional si aplica

    # Estado
    is_active = Column(Boolean, default=True, nullable=False)
    is_featured = Column(Boolean, default=False)  # Producto destacado

    # Rotacion en punto de venta
    rotation_days = Column(Integer, nullable=True)  # Dias promedio de rotacion en gondola
    rotation_flag = Column(String(20), nullable=True)  # ok | slow | critical

    # Imagen
    image_url = Column(String(500), nullable=True)

    # Integracion ERP
    external_id = Column(String(100), nullable=True, index=True)    # ID en el sistema externo del tenant
    external_source = Column(String(50), nullable=True)              # 'siesa', 'world_office', 'sap', etc.

    # RAG — Busqueda semantica
    semantic_tags = Column(JSONB, nullable=True)
    # Estructura esperada:
    # {"synonyms": [], "channel_terms": [], "use_context": [], "strategy": [], "attributes": []}
    # Generado automaticamente al crear/actualizar el producto; enriquecible manualmente.

    embedding = Column(Vector(1024), nullable=True)
    # Vector voyage-3 de 1024 dimensiones.
    # NULL mientras el producto no haya sido indexado por index_product_task.
    # Los productos con embedding NULL se excluyen de search_products sin error.

    # Relationships
    tenant = relationship("Tenant", back_populates="products")
    inventory = relationship("Inventory", back_populates="product", lazy="select", uselist=False)
    promotions = relationship("Promotion", back_populates="product", lazy="select")
    order_items = relationship("OrderItem", back_populates="product", lazy="select")

    def __repr__(self):
        return f"<Product {self.sku} - {self.name}>"


class Promotion(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "promotions"

    tenant_id = Column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    product_id = Column(PGUUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True)

    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # Tipo de promocion
    promo_type = Column(String(50), nullable=False)  # discount | 2x1 | gift | free_shipping | bonus
    discount_percent = Column(Float, nullable=True)
    discount_amount = Column(Float, nullable=True)
    min_quantity = Column(Integer, nullable=True)  # Cantidad minima para aplica promo

    # Vigencia
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Segmentacion (a quienes aplica)
    target_segments = Column(JSON, default=[])  # [] = todos, ["A", "B"] = solo esos segmentos
    target_zones = Column(JSON, default=[])     # [] = todas las zonas

    product = relationship("Product", back_populates="promotions")

    @property
    def is_valid_today(self) -> bool:
        from datetime import date
        today = date.today()
        return self.is_active and self.start_date <= today <= self.end_date

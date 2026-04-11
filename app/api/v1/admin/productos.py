"""
CRUD de productos en el panel admin.
Dispara indexacion semantica via Celery despues de cada creacion o actualizacion.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from pydantic import BaseModel
from typing import Optional
import uuid

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.product import Product

router = APIRouter(prefix="/productos", tags=["Admin - Productos"])


# ── Pydantic models ───────────────────────────────────────────────────────────

class ProductoCreate(BaseModel):
    sku: str
    name: str
    description: Optional[str] = None
    brand: Optional[str] = None
    category: str
    subcategory: Optional[str] = None
    unit: Optional[str] = None
    unit_content: Optional[str] = None
    price: float
    price_promo: Optional[float] = None
    is_active: bool = True
    is_featured: bool = False
    image_url: Optional[str] = None
    external_id: Optional[str] = None
    external_source: Optional[str] = None
    semantic_tags: Optional[dict] = None


class ProductoUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    unit: Optional[str] = None
    unit_content: Optional[str] = None
    price: Optional[float] = None
    price_promo: Optional[float] = None
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None
    image_url: Optional[str] = None
    external_id: Optional[str] = None
    external_source: Optional[str] = None
    semantic_tags: Optional[dict] = None


class ProductoOut(BaseModel):
    id: str
    sku: str
    name: str
    description: Optional[str]
    brand: Optional[str]
    category: str
    subcategory: Optional[str]
    unit: Optional[str]
    price: float
    price_promo: Optional[float]
    is_active: bool
    is_featured: bool
    external_id: Optional[str]
    external_source: Optional[str]
    semantic_tags: Optional[dict]
    is_indexed: bool  # True si el embedding ya fue generado

    class Config:
        from_attributes = True


def _to_out(p: Product) -> ProductoOut:
    return ProductoOut(
        id=str(p.id),
        sku=p.sku,
        name=p.name,
        description=p.description,
        brand=p.brand,
        category=p.category,
        subcategory=p.subcategory,
        unit=p.unit,
        price=p.price,
        price_promo=p.price_promo,
        is_active=p.is_active,
        is_featured=p.is_featured,
        external_id=p.external_id,
        external_source=p.external_source,
        semantic_tags=p.semantic_tags,
        is_indexed=p.embedding is not None,
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/", response_model=list[ProductoOut])
async def list_productos(
    is_active: Optional[bool] = None,
    category: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = current_user["tenant_id"]
    filters = [Product.tenant_id == tenant_id]
    if is_active is not None:
        filters.append(Product.is_active == is_active)
    if category:
        filters.append(Product.category == category)

    result = await db.execute(
        select(Product).where(and_(*filters)).order_by(Product.category, Product.name)
    )
    return [_to_out(p) for p in result.scalars().all()]


@router.post("/", response_model=ProductoOut, status_code=status.HTTP_201_CREATED)
async def create_producto(
    data: ProductoCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = current_user["tenant_id"]

    # Verificar SKU unico dentro del tenant
    existing = await db.execute(
        select(Product).where(
            and_(Product.tenant_id == tenant_id, Product.sku == data.sku)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Ya existe un producto con ese SKU")

    product = Product(
        tenant_id=uuid.UUID(tenant_id),
        **data.model_dump(),
    )
    db.add(product)
    await db.flush()   # Obtener el ID antes del commit
    await db.commit()

    # Disparar indexacion semantica en background via Celery
    # .delay() es no bloqueante — el endpoint responde inmediatamente
    try:
        from app.scheduler.tasks import index_product_task
        index_product_task.delay(str(product.id), tenant_id)
    except Exception as exc:
        # Si Celery no esta disponible no bloqueamos la creacion del producto
        import logging
        logging.getLogger(__name__).warning(
            "celery_not_available_for_indexing",
            product_id=str(product.id),
            error=str(exc),
        )

    return _to_out(product)


@router.get("/{producto_id}", response_model=ProductoOut)
async def get_producto(
    producto_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    product = await _get_or_404(producto_id, current_user["tenant_id"], db)
    return _to_out(product)


@router.patch("/{producto_id}", response_model=ProductoOut)
async def update_producto(
    producto_id: str,
    data: ProductoUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    product = await _get_or_404(producto_id, current_user["tenant_id"], db)

    updated_fields = data.model_dump(exclude_none=True)
    for field, value in updated_fields.items():
        setattr(product, field, value)

    await db.flush()
    await db.commit()

    # Re-indexar si cambio algun campo semanticamente relevante
    semantic_fields = {"name", "description", "brand", "category", "subcategory",
                       "unit", "unit_content", "semantic_tags"}
    if semantic_fields & set(updated_fields.keys()):
        try:
            from app.scheduler.tasks import index_product_task
            index_product_task.delay(str(product.id), current_user["tenant_id"])
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning(
                "celery_not_available_for_reindexing",
                product_id=str(product.id),
                error=str(exc),
            )

    return _to_out(product)


@router.delete("/{producto_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_producto(
    producto_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    product = await _get_or_404(producto_id, current_user["tenant_id"], db)
    product.is_active = False
    await db.flush()


# ── Helper ────────────────────────────────────────────────────────────────────

async def _get_or_404(product_id: str, tenant_id: str, db: AsyncSession) -> Product:
    result = await db.execute(
        select(Product).where(
            and_(Product.id == product_id, Product.tenant_id == tenant_id)
        )
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return product

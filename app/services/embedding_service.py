"""
Servicio de embeddings y busqueda semantica de productos.

Responsabilidades:
  - Construir el texto semantico compuesto de un producto (build_semantic_text)
  - Generar el embedding via Voyage AI voyage-3 (generate_embedding)
  - Indexar un producto en la BD: texto → embedding → UPDATE (index_product)
  - Busqueda semantica por similitud coseno filtrada por tenant (search_products)

Modelo: voyage-3 (1024 dimensiones, mejor soporte para español y dominios B2B)

Nota de diseño — separacion estructural / semantico:
  brand, category y subcategory son filtros estructurales exactos (WHERE SQL).
  No se incluyen en el vector: agregarlos degrada la precision del embedding
  al mezclar senales categoricas con senales semanticas de descripcion.
"""
import asyncio
import logging
from typing import Optional
from uuid import UUID

import voyageai
from sqlalchemy import cast, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.product import Product
from pgvector.sqlalchemy import Vector

logger = logging.getLogger(__name__)

# Numero minimo de tokens aproximados requeridos antes de indexar.
# Se estima como len(text.split()) — suficiente para productos con nombre corto.
MIN_TOKENS = 50

# Dimensiones del modelo voyage-3
EMBEDDING_DIMS = 1024

# Singleton del cliente Voyage AI — evita instanciar una conexion por llamada
_voyage_client = voyageai.AsyncClient(api_key=settings.voyage_api_key)


# ── Construccion del texto semantico ─────────────────────────────────────────

def build_semantic_text(product: Product) -> str:
    """
    Construye el texto semantico compuesto para un producto.

    Incluye exclusivamente campos semanticos: nombre, descripcion, presentacion,
    precio y semantic_tags. Brand, category y subcategory se omiten
    deliberadamente porque son filtros estructurales exactos (WHERE SQL)
    y su inclusion en el vector degrada la precision del embedding.

    Raises:
        ValueError: si el texto resultante tiene menos de MIN_TOKENS tokens.
    """
    parts: list[str] = []

    # Nombre del producto
    if product.name:
        parts.append(f"Producto: {product.name}")

    # Descripcion libre
    if product.description:
        parts.append(f"Descripcion: {product.description}")

    # Unidad de venta
    if product.unit:
        unit_text = product.unit
        if product.unit_content:
            unit_text += f" ({product.unit_content})"
        parts.append(f"Presentacion: {unit_text}")

    # Precio de referencia
    if product.price:
        parts.append(f"Precio: {int(product.price):,} COP")

    # Semantic tags enriquecidas (generadas o editadas manualmente)
    if product.semantic_tags:
        tags: dict = product.semantic_tags

        synonyms = tags.get("synonyms", [])
        if synonyms:
            parts.append(f"Tambien conocido como: {', '.join(synonyms)}")

        channel_terms = tags.get("channel_terms", [])
        if channel_terms:
            parts.append(f"Terminos del canal: {', '.join(channel_terms)}")

        use_context = tags.get("use_context", [])
        if use_context:
            parts.append(f"Contexto de uso: {', '.join(use_context)}")

        strategy = tags.get("strategy", [])
        if strategy:
            parts.append(f"Estrategia comercial: {', '.join(strategy)}")

        attributes = tags.get("attributes", [])
        if attributes:
            parts.append(f"Atributos: {', '.join(attributes)}")

    semantic_text = ". ".join(filter(None, parts))

    token_count = len(semantic_text.split())
    if token_count < MIN_TOKENS:
        raise ValueError(
            f"Texto semantico insuficiente para producto {product.id}: "
            f"{token_count} tokens (minimo {MIN_TOKENS}). "
            f"Agrega descripcion o semantic_tags para enriquecer el producto."
        )

    return semantic_text


# ── Generacion de embedding via Voyage AI ────────────────────────────────────

async def generate_embedding(text: str) -> list[float]:
    """
    Llama a Voyage AI (voyage-3) y retorna el vector de 1024 dimensiones.

    Implementa retry con backoff exponencial: 3 intentos, delays 1s → 2s → 4s.

    Raises:
        Exception: si los 3 intentos fallan.
    """
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            result = await _voyage_client.embed(
                texts=[text],
                model="voyage-3",
                input_type="document",
            )
            return result.embeddings[0]
        except Exception as exc:
            last_exc = exc
            wait = 2 ** attempt  # 1s, 2s, 4s
            logger.warning(
                "voyage_embed_retry",
                attempt=attempt + 1,
                wait_seconds=wait,
                error=str(exc),
            )
            await asyncio.sleep(wait)

    raise last_exc  # type: ignore[misc]


# ── Indexacion de un producto ─────────────────────────────────────────────────

async def index_product(product_id: UUID, db: AsyncSession) -> None:
    """
    Orquesta la indexacion completa de un producto:
      1. Carga el producto desde la BD
      2. Construye el texto semantico compuesto
      3. Genera el embedding via Voyage AI
      4. Hace UPDATE del producto con el nuevo embedding

    Nota: Product.brand/category/subcategory son columnas String, no relaciones.
    No se requiere selectinload ya que ninguna relacion lazy es accedida
    durante build_semantic_text.

    Esta funcion es la que invoca Celery via index_product_task.

    Raises:
        ValueError: si el producto no existe o el texto es insuficiente.
        Exception: si Voyage AI falla despues de 3 reintentos.
    """
    result = await db.execute(
        select(Product).where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()

    if product is None:
        raise ValueError(f"Producto no encontrado: {product_id}")

    semantic_text = build_semantic_text(product)
    logger.info("indexing_product", product_id=str(product_id),
                token_count=len(semantic_text.split()))

    embedding = await generate_embedding(semantic_text)

    await db.execute(
        update(Product)
        .where(Product.id == product_id)
        .values(embedding=embedding)
    )
    await db.commit()

    logger.info("product_indexed", product_id=str(product_id))


# ── Busqueda semantica ────────────────────────────────────────────────────────

async def search_products(
    query: str,
    tenant_id: UUID,
    top_k: int = 10,
    db: AsyncSession = None,  # type: ignore[assignment]
    category: Optional[str] = None,
    subcategory: Optional[str] = None,
    brand: Optional[str] = None,
) -> list[Product]:
    """
    Convierte la query en embedding y busca los productos mas similares
    por distancia coseno usando el indice IVFFlat de pgvector.

    Solo considera productos con embedding IS NOT NULL (ya indexados)
    y filtra por tenant_id para garantizar el aislamiento multi-tenant.

    Los filtros category, subcategory y brand son estructurales (WHERE exacto)
    y se aplican antes del ORDER BY semantico. Son independientes del vector:
    acotan el espacio de busqueda sin degradar la precision del ranking.

    Nota de adaptacion: Product almacena brand/category/subcategory como
    columnas String, no como FKs a tablas de catalogo. Los filtros usan
    igualdad de cadena directamente.

    Args:
        query:       Texto de busqueda en lenguaje natural.
        tenant_id:   UUID del tenant activo.
        top_k:       Numero de resultados a retornar (default 10).
        db:          Sesion async de SQLAlchemy.
        category:    Filtro exacto por nombre de categoria (opcional).
        subcategory: Filtro exacto por nombre de subcategoria (opcional).
        brand:       Filtro exacto por nombre de marca (opcional).

    Returns:
        Lista de Product ordenados de mayor a menor similitud coseno.
        Lista vacia si no hay productos indexados o no hay matches.
    """
    query_embedding = await generate_embedding(query)

    stmt = (
        select(Product)
        .where(
            Product.tenant_id == tenant_id,
            Product.embedding.is_not(None),
            Product.is_active == True,  # noqa: E712
        )
        .order_by(
            Product.embedding.op("<=>")(cast(query_embedding, Vector(EMBEDDING_DIMS)))
        )
        .limit(top_k)
    )

    # Filtros estructurales case-insensitive — acotan el espacio antes del ranking semantico
    if category:
        stmt = stmt.where(Product.category.ilike(category))
    if subcategory:
        stmt = stmt.where(Product.subcategory.ilike(subcategory))
    if brand:
        stmt = stmt.where(Product.brand.ilike(brand))

    result = await db.execute(stmt)
    return list(result.scalars().all())

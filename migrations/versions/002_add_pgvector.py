"""Add pgvector extension, semantic_tags and embedding to products

Revision ID: 002
Revises: 001
Create Date: 2026-04-04

Cambios:
  1. Habilita la extension pgvector en PostgreSQL
  2. Agrega columna semantic_tags JSONB a products
  3. Agrega columna embedding VECTOR(1024) a products
  4. Crea indice IVFFlat para busqueda por similitud coseno
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Habilitar extension pgvector
    # IF NOT EXISTS evita error si ya esta instalada en el cluster
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # 2. Columna semantic_tags: JSONB nullable
    # Estructura esperada:
    # {"synonyms": [], "channel_terms": [], "use_context": [], "strategy": [], "attributes": []}
    op.add_column(
        "products",
        sa.Column("semantic_tags", postgresql.JSONB(), nullable=True),
    )

    # 3. Columna embedding: vector de 1024 dimensiones (voyage-3)
    # nullable=True — los productos se indexan de forma asincrona via Celery
    # Los productos con embedding NULL quedan excluidos de busqueda semantica
    op.execute("ALTER TABLE products ADD COLUMN embedding vector(1024)")

    # 4. Indice IVFFlat para busqueda aproximada eficiente por similitud coseno
    # lists=100 es adecuado para hasta ~1M de vectores.
    # El indice se crea con WHERE embedding IS NOT NULL para no incluir
    # productos aun no indexados y mantener el indice compacto.
    op.execute(
        """
        CREATE INDEX ix_products_embedding
        ON products
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
        WHERE embedding IS NOT NULL
        """
    )


def downgrade() -> None:
    # Eliminar en orden inverso
    op.execute("DROP INDEX IF EXISTS ix_products_embedding")
    op.execute("ALTER TABLE products DROP COLUMN IF EXISTS embedding")
    op.drop_column("products", "semantic_tags")
    # No eliminar la extension vector — puede estar en uso por otras tablas
    # Si se necesita eliminarla: op.execute("DROP EXTENSION IF EXISTS vector")

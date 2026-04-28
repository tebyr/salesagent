"""Sync schema with current models

Revision ID: 003
Revises: 002
Create Date: 2026-04-10

Cambios:
  users:
    - hashed_password → password_hash
    - + phone_normalized (NOT NULL, indexed)

  clients:
    - name → business_name
    - zone → zone_name
    - purchase_frequency_days → avg_purchase_frequency_days
    - DROP credit_limit, overdue_balance
    - + owner_name, nit_cc, email, city, neighborhood, latitude, longitude
    - + phone_normalized (NOT NULL, indexed)
    - + channel_type, avg_ticket_amount
    - + total_purchases_count, total_purchases_amount
    - + notes, preferred_categories, tags

  products:
    - has_low_rotation (Boolean) → rotation_flag (String: ok|slow|critical)
    - + brand, subcategory, unit_content, price_promo
    - + is_featured, rotation_days
    - + index on sku and category

  promotions:
    - name → title
    - valid_from → start_date
    - valid_until → end_date
    - target_segment (String) → target_segments (JSONB)
    - + promo_type, discount_amount, min_quantity, target_zones

  sales_goals:
    - + target_effective_visits, target_active_clients
    - + target_catalog_coverage, target_campaigns, notes

  goal_progress: nueva tabla
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    # ── USERS ──────────────────────────────────────────────────────────────
    # Renombrar hashed_password → password_hash
    op.alter_column("users", "hashed_password", new_column_name="password_hash")

    # Agregar phone_normalized (nullable primero, luego NOT NULL)
    op.add_column("users", sa.Column("phone_normalized", sa.String(20), nullable=True))
    op.execute(
        "UPDATE users SET phone_normalized = regexp_replace(phone, '[^0-9]', '', 'g')"
    )
    op.alter_column("users", "phone_normalized", nullable=False)
    op.create_index("ix_users_phone_normalized", "users", ["phone_normalized"])

    # ── CLIENTS ────────────────────────────────────────────────────────────
    # Renombrar columnas
    op.alter_column("clients", "name", new_column_name="business_name")
    op.alter_column("clients", "zone", new_column_name="zone_name")
    op.alter_column("clients", "purchase_frequency_days",
                    new_column_name="avg_purchase_frequency_days")

    # Eliminar columnas obsoletas
    op.drop_column("clients", "credit_limit")
    op.drop_column("clients", "overdue_balance")

    # Agregar campos de identificacion y contacto
    op.add_column("clients", sa.Column("owner_name", sa.String(200), nullable=True))
    op.add_column("clients", sa.Column("nit_cc", sa.String(20), nullable=True))
    op.add_column("clients", sa.Column("email", sa.String(200), nullable=True))

    # Agregar campos de ubicacion
    op.add_column("clients", sa.Column("city", sa.String(100), nullable=True))
    op.add_column("clients", sa.Column("neighborhood", sa.String(100), nullable=True))
    op.add_column("clients", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("clients", sa.Column("longitude", sa.Float(), nullable=True))

    # phone_normalized (nullable primero, luego NOT NULL)
    op.add_column("clients", sa.Column("phone_normalized", sa.String(20), nullable=True))
    op.execute(
        "UPDATE clients SET phone_normalized = regexp_replace(phone, '[^0-9]', '', 'g')"
    )
    op.alter_column("clients", "phone_normalized", nullable=False)
    op.create_index("ix_clients_phone_normalized", "clients", ["phone_normalized"])

    # Agregar campos de segmentacion y metricas
    op.add_column("clients", sa.Column(
        "channel_type", sa.String(50), nullable=True, server_default="tradicional"
    ))
    op.add_column("clients", sa.Column("avg_ticket_amount", sa.Float(), nullable=True))
    op.add_column("clients", sa.Column(
        "total_purchases_count", sa.Integer(), nullable=False, server_default="0"
    ))
    op.add_column("clients", sa.Column(
        "total_purchases_amount", sa.Float(), nullable=False, server_default="0"
    ))

    # Agregar campos de notas y contexto para el agente
    op.add_column("clients", sa.Column("notes", sa.Text(), nullable=True))
    op.add_column("clients", sa.Column(
        "preferred_categories", postgresql.JSON(), nullable=True, server_default=sa.text("'[]'::json")
    ))
    op.add_column("clients", sa.Column(
        "tags", postgresql.JSON(), nullable=True, server_default=sa.text("'[]'::json")
    ))

    # ── PRODUCTS ───────────────────────────────────────────────────────────
    # Agregar campos faltantes
    op.add_column("products", sa.Column("brand", sa.String(100), nullable=True))
    op.add_column("products", sa.Column("subcategory", sa.String(100), nullable=True))
    op.add_column("products", sa.Column("unit_content", sa.String(50), nullable=True))
    op.add_column("products", sa.Column("price_promo", sa.Float(), nullable=True))
    op.add_column("products", sa.Column(
        "is_featured", sa.Boolean(), nullable=False, server_default="false"
    ))
    op.add_column("products", sa.Column("rotation_days", sa.Integer(), nullable=True))

    # Reemplazar has_low_rotation (Boolean) por rotation_flag (String)
    op.add_column("products", sa.Column("rotation_flag", sa.String(20), nullable=True))
    op.execute("UPDATE products SET rotation_flag = 'slow' WHERE has_low_rotation = true")
    op.drop_column("products", "has_low_rotation")

    # Crear indices faltantes
    op.create_index("ix_products_sku", "products", ["sku"])
    op.create_index("ix_products_category", "products", ["category"])

    # ── PROMOTIONS ─────────────────────────────────────────────────────────
    # Renombrar columnas
    op.alter_column("promotions", "name", new_column_name="title")
    op.alter_column("promotions", "valid_from", new_column_name="start_date")
    op.alter_column("promotions", "valid_until", new_column_name="end_date")

    # target_segment (String) → target_segments (JSONB)
    op.add_column("promotions", sa.Column(
        "target_segments", postgresql.JSONB(), nullable=True, server_default=sa.text("'[]'::jsonb")
    ))
    op.execute(
        """
        UPDATE promotions
        SET target_segments = to_jsonb(ARRAY[target_segment])
        WHERE target_segment IS NOT NULL AND target_segment != ''
        """
    )
    op.drop_column("promotions", "target_segment")

    # Agregar campos faltantes
    op.add_column("promotions", sa.Column("promo_type", sa.String(50), nullable=True))
    op.add_column("promotions", sa.Column("discount_amount", sa.Float(), nullable=True))
    op.add_column("promotions", sa.Column("min_quantity", sa.Integer(), nullable=True))
    op.add_column("promotions", sa.Column(
        "target_zones", postgresql.JSONB(), nullable=True, server_default=sa.text("'[]'::jsonb")
    ))

    # ── SALES_GOALS ────────────────────────────────────────────────────────
    op.add_column("sales_goals", sa.Column(
        "target_effective_visits", sa.Integer(), nullable=True
    ))
    op.add_column("sales_goals", sa.Column(
        "target_active_clients", sa.Integer(), nullable=True
    ))
    op.add_column("sales_goals", sa.Column(
        "target_catalog_coverage", sa.Float(), nullable=True
    ))
    op.add_column("sales_goals", sa.Column(
        "target_campaigns", postgresql.JSON(), nullable=True, server_default=sa.text("'{}'::json")
    ))
    op.add_column("sales_goals", sa.Column("notes", sa.String(500), nullable=True))

    # ── GOAL_PROGRESS ──────────────────────────────────────────────────────
    op.create_table(
        "goal_progress",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("goal_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("sales_goals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("salesperson_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False, index=True),
        sa.Column("actual_amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("actual_visits", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("actual_effective_visits", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("actual_active_clients", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pct_amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("pct_visits", sa.Float(), nullable=False, server_default="0"),
        sa.Column("projected_amount", sa.Float(), nullable=True),
        sa.Column("projected_pct", sa.Float(), nullable=True),
        sa.Column("days_elapsed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("days_remaining", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_goal_progress_tenant_id", "goal_progress", ["tenant_id"])
    op.create_index("ix_goal_progress_goal_id", "goal_progress", ["goal_id"])
    op.create_index("ix_goal_progress_salesperson_id", "goal_progress", ["salesperson_id"])


def downgrade() -> None:
    # goal_progress
    op.drop_table("goal_progress")

    # sales_goals
    op.drop_column("sales_goals", "notes")
    op.drop_column("sales_goals", "target_campaigns")
    op.drop_column("sales_goals", "target_catalog_coverage")
    op.drop_column("sales_goals", "target_active_clients")
    op.drop_column("sales_goals", "target_effective_visits")

    # promotions
    op.drop_column("promotions", "target_zones")
    op.drop_column("promotions", "min_quantity")
    op.drop_column("promotions", "discount_amount")
    op.drop_column("promotions", "promo_type")
    op.add_column("promotions", sa.Column("target_segment", sa.String(50), nullable=True))
    op.execute(
        "UPDATE promotions SET target_segment = target_segments->>0 WHERE jsonb_array_length(target_segments) > 0"
    )
    op.drop_column("promotions", "target_segments")
    op.alter_column("promotions", "end_date", new_column_name="valid_until")
    op.alter_column("promotions", "start_date", new_column_name="valid_from")
    op.alter_column("promotions", "title", new_column_name="name")

    # products
    op.drop_index("ix_products_category", "products")
    op.drop_index("ix_products_sku", "products")
    op.add_column("products", sa.Column(
        "has_low_rotation", sa.Boolean(), nullable=False, server_default="false"
    ))
    op.execute("UPDATE products SET has_low_rotation = true WHERE rotation_flag IS NOT NULL")
    op.drop_column("products", "rotation_flag")
    op.drop_column("products", "rotation_days")
    op.drop_column("products", "is_featured")
    op.drop_column("products", "price_promo")
    op.drop_column("products", "unit_content")
    op.drop_column("products", "subcategory")
    op.drop_column("products", "brand")

    # clients
    op.drop_column("clients", "tags")
    op.drop_column("clients", "preferred_categories")
    op.drop_column("clients", "notes")
    op.drop_column("clients", "total_purchases_amount")
    op.drop_column("clients", "total_purchases_count")
    op.drop_column("clients", "avg_ticket_amount")
    op.drop_column("clients", "channel_type")
    op.drop_index("ix_clients_phone_normalized", "clients")
    op.drop_column("clients", "phone_normalized")
    op.drop_column("clients", "longitude")
    op.drop_column("clients", "latitude")
    op.drop_column("clients", "neighborhood")
    op.drop_column("clients", "city")
    op.drop_column("clients", "email")
    op.drop_column("clients", "nit_cc")
    op.drop_column("clients", "owner_name")
    op.add_column("clients", sa.Column("overdue_balance", sa.Float(), nullable=True,
                                       server_default="0"))
    op.add_column("clients", sa.Column("credit_limit", sa.Float(), nullable=True))
    op.alter_column("clients", "avg_purchase_frequency_days",
                    new_column_name="purchase_frequency_days")
    op.alter_column("clients", "zone_name", new_column_name="zone")
    op.alter_column("clients", "business_name", new_column_name="name")

    # users
    op.drop_index("ix_users_phone_normalized", "users")
    op.drop_column("users", "phone_normalized")
    op.alter_column("users", "password_hash", new_column_name="hashed_password")

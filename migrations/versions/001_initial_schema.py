"""Initial schema — todas las tablas del sistema

Revision ID: 001
Revises:
Create Date: 2026-03-25
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # TENANTS
    # ------------------------------------------------------------------ #
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("nit", sa.String(20), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("whatsapp_phone_number_id", sa.String(50), nullable=True),
        sa.Column("whatsapp_business_account_id", sa.String(50), nullable=True),
        sa.Column("whatsapp_access_token", sa.Text(), nullable=True),
        sa.Column("whatsapp_phone_display", sa.String(20), nullable=True),
        sa.Column("agent_name", sa.String(100), nullable=False,
                  server_default="Agente Comercial"),
        sa.Column("agent_personality", sa.Text(), nullable=True),
        sa.Column("logo_url", sa.String(500), nullable=True),
        sa.Column("primary_color", sa.String(7), nullable=False, server_default="#2563EB"),
        sa.Column("email_footer", sa.Text(), nullable=True),
        sa.Column("schedule_config", postgresql.JSONB(), nullable=True),
        sa.Column("email_config", postgresql.JSONB(), nullable=True),
        sa.Column("plan", sa.String(50), nullable=False, server_default="starter"),
        sa.Column("max_salespersons", sa.Integer(), nullable=True, server_default="50"),
    )
    op.create_index("ix_tenants_slug", "tenants", ["slug"])
    op.create_index("ix_tenants_whatsapp_phone_number_id", "tenants",
                    ["whatsapp_phone_number_id"])

    # ------------------------------------------------------------------ #
    # USERS (vendedores, supervisores, gerentes, admins)
    # ------------------------------------------------------------------ #
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("phone", sa.String(20), nullable=False),
        sa.Column("email", sa.String(200), nullable=True),
        sa.Column("hashed_password", sa.String(200), nullable=True),
        sa.Column("role", sa.String(20), nullable=False, server_default="salesperson"),
        sa.Column("zone", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("whatsapp_opt_in", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("external_id", sa.String(100), nullable=True),
        sa.Column("external_source", sa.String(50), nullable=True),
        sa.UniqueConstraint("tenant_id", "phone", name="uq_users_tenant_phone"),
        sa.UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
        sa.UniqueConstraint("tenant_id", "external_id", name="uq_users_tenant_external_id"),
    )
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])
    op.create_index("ix_users_phone", "users", ["phone"])
    op.create_index("ix_users_external_id", "users", ["external_id"])

    # ------------------------------------------------------------------ #
    # CLIENTS (tenderos)
    # ------------------------------------------------------------------ #
    op.create_table(
        "clients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("salesperson_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("zone_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("zones.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("phone", sa.String(20), nullable=False),
        sa.Column("address", sa.String(500), nullable=True),
        sa.Column("zone", sa.String(100), nullable=True),
        sa.Column("segment", sa.String(50), nullable=True, server_default="regular"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("whatsapp_opt_in", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("credit_limit", sa.Float(), nullable=True),
        sa.Column("overdue_balance", sa.Float(), nullable=True, server_default="0"),
        sa.Column("last_purchase_date", sa.Date(), nullable=True),
        sa.Column("purchase_frequency_days", sa.Integer(), nullable=True),
        sa.Column("external_id", sa.String(100), nullable=True),
        sa.Column("external_source", sa.String(50), nullable=True),
        sa.UniqueConstraint("tenant_id", "phone", name="uq_clients_tenant_phone"),
        sa.UniqueConstraint("tenant_id", "external_id", name="uq_clients_tenant_external_id"),
    )
    op.create_index("ix_clients_tenant_id", "clients", ["tenant_id"])
    op.create_index("ix_clients_phone", "clients", ["phone"])
    op.create_index("ix_clients_salesperson_id", "clients", ["salesperson_id"])
    op.create_index("ix_clients_zone_id", "clients", ["zone_id"])
    op.create_index("ix_clients_external_id", "clients", ["external_id"])

    # ------------------------------------------------------------------ #
    # PRODUCTS
    # ------------------------------------------------------------------ #
    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sku", sa.String(100), nullable=True),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(50), nullable=True, server_default="unidad"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("has_low_rotation", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("image_url", sa.String(500), nullable=True),
        sa.Column("external_id", sa.String(100), nullable=True),
        sa.Column("external_source", sa.String(50), nullable=True),
        sa.UniqueConstraint("tenant_id", "external_id", name="uq_products_tenant_external_id"),
    )
    op.create_index("ix_products_tenant_id", "products", ["tenant_id"])
    op.create_index("ix_products_external_id", "products", ["external_id"])

    # Promotions
    op.create_table(
        "promotions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("discount_percent", sa.Float(), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_until", sa.Date(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("target_segment", sa.String(50), nullable=True),
    )
    op.create_index("ix_promotions_tenant_id", "promotions", ["tenant_id"])

    # ------------------------------------------------------------------ #
    # INVENTORY
    # ------------------------------------------------------------------ #
    op.create_table(
        "inventory",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("quantity_available", sa.Float(), nullable=False, server_default="0"),
        sa.Column("quantity_reserved", sa.Float(), nullable=False, server_default="0"),
        sa.Column("min_stock_alert", sa.Float(), nullable=True),
        sa.UniqueConstraint("tenant_id", "product_id", name="uq_inventory_tenant_product"),
    )
    op.create_index("ix_inventory_tenant_id", "inventory", ["tenant_id"])

    # ------------------------------------------------------------------ #
    # ZONES
    # ------------------------------------------------------------------ #
    op.create_table(
        "zones",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.create_index("ix_zones_tenant_id", "zones", ["tenant_id"])

    # ------------------------------------------------------------------ #
    # ROUTES
    # ------------------------------------------------------------------ #
    op.create_table(
        "routes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("zone_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("zones.id", ondelete="SET NULL"), nullable=True),
        sa.Column("salesperson_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=True),
        sa.Column("route_type", sa.String(20), nullable=False, server_default="presential"),
        sa.Column("operating_days", postgresql.JSONB(), nullable=True),
        sa.Column("delivery_days", postgresql.JSONB(), nullable=True),
        sa.Column("daily_schedule", postgresql.JSONB(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("total_clients", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("visited_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sales_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_sales_amount", sa.String(50), nullable=False, server_default="0"),
    )
    op.create_index("ix_routes_tenant_id", "routes", ["tenant_id"])
    op.create_index("ix_routes_zone_id", "routes", ["zone_id"])
    op.create_index("ix_routes_vendor_date", "routes", ["salesperson_id"])
    op.create_index("ix_routes_type", "routes", ["route_type"])

    op.create_table(
        "route_visits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("route_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("routes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("visit_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("visit_type", sa.String(20), nullable=False, server_default="presential"),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("pre_visit_notification_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("visited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("escalated_to_salesperson_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("escalated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_route_visits_tenant_id", "route_visits", ["tenant_id"])
    op.create_index("ix_route_visits_route_id", "route_visits", ["route_id"])
    op.create_index("ix_route_visits_client_id", "route_visits", ["client_id"])
    op.create_index("ix_route_visits_escalated", "route_visits", ["escalated_to_salesperson_id"])

    # ------------------------------------------------------------------ #
    # ORDERS
    # ------------------------------------------------------------------ #
    op.create_table(
        "orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("salesperson_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("order_number", sa.String(50), nullable=True),
        sa.Column("order_date", sa.Date(), nullable=False),
        sa.Column("delivery_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("source", sa.String(20), nullable=False, server_default="salesperson"),
        sa.Column("subtotal", sa.Float(), nullable=False, server_default="0"),
        sa.Column("discount_amount", sa.Float(), server_default="0"),
        sa.Column("total_amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("external_id", sa.String(100), nullable=True),
        sa.Column("external_source", sa.String(50), nullable=True),
        sa.UniqueConstraint("tenant_id", "external_id", name="uq_orders_tenant_external_id"),
    )
    op.create_index("ix_orders_tenant_id", "orders", ["tenant_id"])
    op.create_index("ix_orders_client_id", "orders", ["client_id"])
    op.create_index("ix_orders_order_date", "orders", ["order_date"])
    op.create_index("ix_orders_external_id", "orders", ["external_id"])

    op.create_table(
        "order_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("unit_price", sa.Float(), nullable=False),
        sa.Column("discount_percent", sa.Float(), server_default="0"),
        sa.Column("total_price", sa.Float(), nullable=False),
    )
    op.create_index("ix_order_items_order_id", "order_items", ["order_id"])

    # ------------------------------------------------------------------ #
    # GOALS
    # ------------------------------------------------------------------ #
    op.create_table(
        "sales_goals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("salesperson_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("period_type", sa.String(20), nullable=False, server_default="monthly"),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("target_amount", sa.Float(), nullable=False),
        sa.Column("target_visits", sa.Integer(), nullable=True),
        sa.Column("target_new_clients", sa.Integer(), nullable=True),
        sa.Column("target_by_category", postgresql.JSONB(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.create_index("ix_sales_goals_tenant_id", "sales_goals", ["tenant_id"])
    op.create_index("ix_sales_goals_vendor_period", "sales_goals",
                    ["salesperson_id", "period_start", "period_end"])

    # ------------------------------------------------------------------ #
    # CONVERSATIONS
    # ------------------------------------------------------------------ #
    op.create_table(
        "wa_conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("phone_normalized", sa.String(20), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("state", sa.String(30), nullable=False, server_default="idle"),
        sa.Column("context", postgresql.JSONB(), nullable=True, server_default="{}"),
        sa.Column("recent_messages", postgresql.JSONB(), nullable=True, server_default="[]"),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_outbound_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("wa_window_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_window_open", sa.Boolean(), nullable=False, server_default="false"),
        sa.UniqueConstraint("tenant_id", "phone_normalized", name="uq_conv_tenant_phone"),
    )
    op.create_index("ix_wa_conversations_tenant_id", "wa_conversations", ["tenant_id"])
    op.create_index("ix_wa_conversations_phone", "wa_conversations", ["phone_normalized"])

    op.create_table(
        "message_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("wa_conversations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("wa_message_id", sa.String(100), nullable=True),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("phone", sa.String(20), nullable=False),
        sa.Column("message_type", sa.String(50), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), nullable=True),
        sa.Column("triggered_by", sa.String(100), nullable=True),
        sa.Column("ai_model_used", sa.String(50), nullable=True),
        sa.Column("ai_tokens_used", sa.Integer(), nullable=True),
    )
    op.create_index("ix_message_logs_tenant_id", "message_logs", ["tenant_id"])
    op.create_index("ix_message_logs_wa_message_id", "message_logs", ["wa_message_id"])

    # ------------------------------------------------------------------ #
    # NOTIFICATIONS
    # ------------------------------------------------------------------ #
    op.create_table(
        "notification_schedules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("recipient_phone", sa.String(20), nullable=False),
        sa.Column("recipient_role", sa.String(20), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("context_data", postgresql.JSONB(), nullable=True),
        sa.Column("is_sent", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_notification_schedules_tenant_id", "notification_schedules", ["tenant_id"])
    op.create_index("ix_notification_schedules_scheduled", "notification_schedules",
                    ["scheduled_for", "is_sent"])

    # ------------------------------------------------------------------ #
    # ANALYTICS
    # ------------------------------------------------------------------ #
    op.create_table(
        "client_product_affinities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("affinity_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("purchase_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_purchased_at", sa.Date(), nullable=True),
        sa.Column("avg_quantity", sa.Float(), nullable=True),
        sa.UniqueConstraint("tenant_id", "client_id", "product_id",
                            name="uq_affinity_tenant_client_product"),
    )
    op.create_index("ix_affinities_tenant_client", "client_product_affinities",
                    ["tenant_id", "client_id"])

    op.create_table(
        "daily_sales_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("salesperson_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("total_sales", sa.Float(), nullable=False, server_default="0"),
        sa.Column("total_visits", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("effective_visits", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("new_clients", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("tenant_id", "snapshot_date", "salesperson_id",
                            name="uq_snapshot_tenant_date_vendor"),
    )
    op.create_index("ix_snapshots_tenant_date", "daily_sales_snapshots",
                    ["tenant_id", "snapshot_date"])


def downgrade() -> None:
    op.drop_table("daily_sales_snapshots")
    op.drop_table("client_product_affinities")
    op.drop_table("notification_schedules")
    op.drop_table("message_logs")
    op.drop_table("wa_conversations")
    op.drop_table("sales_goals")
    op.drop_table("order_items")
    op.drop_table("orders")
    op.drop_table("route_visits")
    op.drop_table("routes")
    op.drop_table("zones")
    op.drop_table("inventory")
    op.drop_table("promotions")
    op.drop_table("products")
    op.drop_table("clients")
    op.drop_table("users")
    op.drop_table("tenants")

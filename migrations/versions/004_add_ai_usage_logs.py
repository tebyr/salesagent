"""Add ai_usage_logs table + fix message_logs.ai_tokens_used type

Revision ID: 004
Revises: 003
Create Date: 2026-04-27

Cambios:
  ai_usage_logs (nueva tabla):
    - Registro de cada llamada a un LLM con tokens y costo_usd
    - Provider-agnostic: anthropic | openai | google | mistral
    - Índice compuesto (tenant_id, created_at) para queries de costo mensual

  message_logs:
    - ai_tokens_used: tipo incorrecto → INTEGER (corregido)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Crear tabla ai_usage_logs ─────────────────────────────────────────
    op.create_table(
        'ai_usage_logs',
        sa.Column('id',              postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at',      sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at',      sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),

        # Tenant
        sa.Column('tenant_id',       postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id'), nullable=False),

        # Proveedor y modelo
        sa.Column('provider',        sa.String(20),  nullable=False),
        sa.Column('model',           sa.String(100), nullable=False),

        # Origen de la llamada
        sa.Column('agent_class',     sa.String(50),  nullable=False),
        sa.Column('triggered_by',    sa.String(100), nullable=True),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('wa_conversations.id'), nullable=True),

        # Tokens y costo
        sa.Column('input_tokens',    sa.Integer(),       nullable=False, server_default='0'),
        sa.Column('output_tokens',   sa.Integer(),       nullable=False, server_default='0'),
        sa.Column('total_tokens',    sa.Integer(),       nullable=False, server_default='0'),
        sa.Column('cost_usd',        sa.Numeric(10, 6),  nullable=False, server_default='0'),
    )

    # Índices
    op.create_index('ix_ai_usage_logs_tenant_id',
                    'ai_usage_logs', ['tenant_id'])
    op.create_index('ix_ai_usage_logs_conversation_id',
                    'ai_usage_logs', ['conversation_id'])
    # Índice compuesto para queries de costo mensual: WHERE tenant_id=X AND created_at>=Y
    op.create_index('ix_ai_usage_logs_tenant_created',
                    'ai_usage_logs', ['tenant_id', 'created_at'])

    # ── 2. Corregir tipo de message_logs.ai_tokens_used ──────────────────────
    # El tipo original era incorrecto (Column(String).__class__ = String)
    # Lo convertimos a INTEGER con USING para no perder datos existentes
    op.alter_column(
        'message_logs',
        'ai_tokens_used',
        existing_type=sa.String(),
        type_=sa.Integer(),
        existing_nullable=True,
        postgresql_using='ai_tokens_used::integer',
    )


def downgrade() -> None:
    # Revertir ai_tokens_used a String
    op.alter_column(
        'message_logs',
        'ai_tokens_used',
        existing_type=sa.Integer(),
        type_=sa.String(),
        existing_nullable=True,
    )

    # Eliminar índices y tabla
    op.drop_index('ix_ai_usage_logs_tenant_created', table_name='ai_usage_logs')
    op.drop_index('ix_ai_usage_logs_conversation_id', table_name='ai_usage_logs')
    op.drop_index('ix_ai_usage_logs_tenant_id',      table_name='ai_usage_logs')
    op.drop_table('ai_usage_logs')

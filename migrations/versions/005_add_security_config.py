"""005 — add security_config to tenants

Agrega columna JSONB security_config al tenant para parametrizar
el timeout de sesión del panel admin (visible/editable solo por admins).

Revision ID: 005
Revises: 004
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None

SECURITY_DEFAULTS = {
    "session_timeout_minutes": 30,
    "session_warning_minutes": 2,
}


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column(
            "security_config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default=sa.text(f"'{{}}'::jsonb"),
        ),
    )
    # Poblar con defaults en todas las filas existentes
    op.execute(
        f"""
        UPDATE tenants
        SET security_config = '{{"session_timeout_minutes": 30, "session_warning_minutes": 2}}'::jsonb
        WHERE security_config IS NULL OR security_config = '{{}}'::jsonb
        """
    )


def downgrade() -> None:
    op.drop_column("tenants", "security_config")

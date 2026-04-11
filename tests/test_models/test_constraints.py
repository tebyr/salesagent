"""
Tests de restricciones y estructura de modelos.

Verifica a nivel de Python (sin BD) que:
  - Los modelos tienen los campos correctos (post-migracion 003)
  - No existen campos obsoletos que causarian errores en runtime
  - Los enums tienen los valores esperados
  - Los relationships tienen los nombres correctos (sin conflicto zone vs zone_name)
"""
import pytest
from sqlalchemy.orm import RelationshipProperty
from sqlalchemy import inspect as sa_inspect


# ── Utilidad ──────────────────────────────────────────────────────────────

def column_names(model_class) -> set[str]:
    """Retorna los nombres de todas las columnas del modelo."""
    mapper = sa_inspect(model_class)
    return {c.key for c in mapper.columns}


def relationship_names(model_class) -> set[str]:
    """Retorna los nombres de todos los relationships del modelo."""
    mapper = sa_inspect(model_class)
    return {r.key for r in mapper.relationships}


# ── User ──────────────────────────────────────────────────────────────────

class TestUserModel:

    def test_user_has_password_hash_not_hashed_password(self):
        """Migracion 003: hashed_password fue renombrado a password_hash."""
        from app.models.user import User
        cols = column_names(User)
        assert "password_hash" in cols, "Falta campo 'password_hash'"
        assert "hashed_password" not in cols, "Campo obsoleto 'hashed_password' sigue existiendo"

    def test_user_has_phone_normalized(self):
        """phone_normalized es requerido para identificar usuarios por WhatsApp."""
        from app.models.user import User
        cols = column_names(User)
        assert "phone_normalized" in cols

    def test_user_role_enum_values(self):
        """Los roles deben incluir SALESPERSON y AGENT (no VENDOR)."""
        from app.models.user import UserRole
        values = {r.value for r in UserRole}
        assert "salesperson" in values
        assert "agent" in values
        assert "manager" in values
        assert "vendor" not in values, "Rol obsoleto 'vendor' encontrado"

    def test_user_required_fields_present(self):
        from app.models.user import User
        cols = column_names(User)
        for field in ("tenant_id", "name", "phone", "role", "is_active", "whatsapp_opt_in"):
            assert field in cols, f"Campo requerido '{field}' falta en User"


# ── Client ────────────────────────────────────────────────────────────────

class TestClientModel:

    def test_client_has_business_name_not_name(self):
        """Migracion 003: name fue renombrado a business_name."""
        from app.models.client import Client
        cols = column_names(Client)
        assert "business_name" in cols, "Falta campo 'business_name'"
        # 'name' puede existir como campo heredado de Python pero no como columna SA
        # Verificamos que el mapper lo exponga como 'business_name'
        assert "name" not in cols, "Columna obsoleta 'name' sigue expuesta en Client"

    def test_client_has_zone_name_column_not_zone(self):
        """
        Client tiene zone_name (columna texto) y zone (relationship FK).
        Antes habia conflicto porque ambos se llamaban 'zone'.
        """
        from app.models.client import Client
        cols = column_names(Client)
        rels = relationship_names(Client)
        # La columna de texto libre debe llamarse zone_name
        assert "zone_name" in cols, "Falta columna 'zone_name'"
        # El relationship con Zone debe llamarse 'zone'
        assert "zone" in rels, "Falta relationship 'zone'"
        # La columna 'zone' no debe existir (era el conflicto)
        assert "zone" not in cols, "Columna 'zone' en conflicto con relationship 'zone'"

    def test_client_has_phone_normalized(self):
        from app.models.client import Client
        assert "phone_normalized" in column_names(Client)

    def test_client_has_avg_purchase_frequency_days_not_purchase_frequency_days(self):
        """Migracion 003: purchase_frequency_days → avg_purchase_frequency_days."""
        from app.models.client import Client
        cols = column_names(Client)
        assert "avg_purchase_frequency_days" in cols
        assert "purchase_frequency_days" not in cols

    def test_client_has_no_credit_limit(self):
        """credit_limit fue eliminado en migracion 003."""
        from app.models.client import Client
        assert "credit_limit" not in column_names(Client)

    def test_client_has_zone_id_fk(self):
        """zone_id es FK a zones.id (modelo Zone)."""
        from app.models.client import Client
        assert "zone_id" in column_names(Client)

    def test_client_required_fields_present(self):
        from app.models.client import Client
        cols = column_names(Client)
        for field in ("tenant_id", "business_name", "phone", "phone_normalized",
                      "is_active", "segment", "channel_type"):
            assert field in cols, f"Campo requerido '{field}' falta en Client"


# ── Product ───────────────────────────────────────────────────────────────

class TestProductModel:

    def test_product_has_rotation_flag_not_has_low_rotation(self):
        """Migracion 003: has_low_rotation (Bool) → rotation_flag (String)."""
        from app.models.product import Product
        cols = column_names(Product)
        assert "rotation_flag" in cols
        assert "has_low_rotation" not in cols

    def test_product_has_sku(self):
        from app.models.product import Product
        assert "sku" in column_names(Product)

    def test_product_has_brand_and_subcategory(self):
        from app.models.product import Product
        cols = column_names(Product)
        assert "brand" in cols
        assert "subcategory" in cols

    def test_product_has_price_promo_and_unit_content(self):
        from app.models.product import Product
        cols = column_names(Product)
        assert "price_promo" in cols
        assert "unit_content" in cols

    def test_product_has_embedding_and_semantic_tags(self):
        from app.models.product import Product
        cols = column_names(Product)
        assert "embedding" in cols
        assert "semantic_tags" in cols


# ── Zone / Route ──────────────────────────────────────────────────────────

class TestZoneRouteModels:

    def test_zone_has_required_fields(self):
        from app.models.route import Zone
        cols = column_names(Zone)
        for field in ("tenant_id", "name", "is_active"):
            assert field in cols

    def test_route_type_enum_values(self):
        from app.models.route import RouteType
        values = {r.value for r in RouteType}
        assert "presential" in values
        assert "agent_wa" in values

    def test_route_has_operating_days_and_delivery_days(self):
        from app.models.route import Route
        cols = column_names(Route)
        assert "operating_days" in cols
        assert "delivery_days" in cols

    def test_route_has_no_date_column(self):
        """Route usa operating_days JSONB, no una columna 'date'."""
        from app.models.route import Route
        assert "date" not in column_names(Route)


# ── SalesGoal ─────────────────────────────────────────────────────────────

class TestSalesGoalModel:

    def test_goal_period_type_enum(self):
        from app.models.goal import GoalPeriodType
        values = {p.value for p in GoalPeriodType}
        assert "monthly" in values
        assert "weekly" in values
        assert "daily" in values

    def test_goal_has_period_type_as_enum_column(self):
        from app.models.goal import SalesGoal
        assert "period_type" in column_names(SalesGoal)

    def test_goal_has_extra_targets(self):
        """Migracion 003: se agregaron campos target_effective_visits y target_active_clients."""
        from app.models.goal import SalesGoal
        cols = column_names(SalesGoal)
        assert "target_effective_visits" in cols
        assert "target_active_clients" in cols

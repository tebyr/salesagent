"""
Tests de app.services.embedding_service.

Cubre (sin llamadas reales a Voyage AI ni BD):
  - build_semantic_text: campos incluidos vs excluidos
  - build_semantic_text: MIN_TOKENS validacion
  - build_semantic_text: semantic_tags enriquecidas
  - generate_embedding: retry con backoff (mock)
  - search_products: filtros estructurales + llamada a BD (mock)
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ── Fixture: producto con texto semantico suficiente ───────────────────────

def _make_rich_product(**kwargs):
    """Crea un MagicMock de Product con texto suficiente para superar MIN_TOKENS."""
    p = MagicMock()
    p.id = "dddddddd-0000-0000-0000-000000000004"
    p.name = "Arroz Diana Premium x 5 Kilogramos Bolsa Familiar"
    p.description = (
        "Arroz blanco de grano largo seleccionado, ideal para todo tipo de "
        "preparaciones culinarias. Sin aditivos, sin conservantes. Textura "
        "suave y sabor neutro. Cultivado en los llanos orientales de Colombia."
    )
    p.brand = "Diana"
    p.category = "granos"
    p.subcategory = "arroz"
    p.unit = "Bulto"
    p.unit_content = "10 bolsas de 500g"
    p.price = 220_000.0
    p.price_promo = None
    p.semantic_tags = None
    for k, v in kwargs.items():
        setattr(p, k, v)
    return p


# ── build_semantic_text ───────────────────────────────────────────────────

class TestBuildSemanticText:

    def test_includes_product_name(self):
        from app.services.embedding_service import build_semantic_text
        p = _make_rich_product()
        text = build_semantic_text(p)
        assert p.name in text

    def test_includes_description(self):
        from app.services.embedding_service import build_semantic_text
        p = _make_rich_product()
        text = build_semantic_text(p)
        assert "Cultivado en los llanos orientales" in text

    def test_includes_unit_and_unit_content(self):
        from app.services.embedding_service import build_semantic_text
        p = _make_rich_product()
        text = build_semantic_text(p)
        assert "Bulto" in text
        assert "10 bolsas de 500g" in text

    def test_includes_price(self):
        from app.services.embedding_service import build_semantic_text
        p = _make_rich_product()
        text = build_semantic_text(p)
        assert "220" in text  # precio formateado como 220,000 COP

    def test_excludes_brand(self):
        """
        brand es filtro estructural (WHERE SQL), no debe estar en el vector.
        Excluirlo mejora la precision semantica del embedding.
        """
        from app.services.embedding_service import build_semantic_text
        p = _make_rich_product()
        text = build_semantic_text(p)
        # El nombre de marca "Diana" aparece en el nombre del producto,
        # pero NO debe aparecer como campo independiente "Marca: Diana"
        assert "Marca:" not in text

    def test_excludes_category(self):
        """category es filtro estructural, no debe estar en el vector."""
        from app.services.embedding_service import build_semantic_text
        p = _make_rich_product()
        text = build_semantic_text(p)
        assert "Categoria:" not in text
        assert "Subcategoria:" not in text

    def test_raises_value_error_when_too_short(self):
        """
        Si el texto semantico tiene menos de MIN_TOKENS palabras,
        debe lanzar ValueError con mensaje descriptivo.
        """
        from app.services.embedding_service import build_semantic_text, MIN_TOKENS
        p = MagicMock()
        p.name = "Arroz"          # muy corto
        p.description = None
        p.unit = None
        p.unit_content = None
        p.price = None
        p.semantic_tags = None

        with pytest.raises(ValueError, match=str(MIN_TOKENS)):
            build_semantic_text(p)

    def test_semantic_tags_synonyms_included(self):
        """semantic_tags.synonyms deben aparecer en el texto."""
        from app.services.embedding_service import build_semantic_text
        p = _make_rich_product(semantic_tags={
            "synonyms": ["arrocito", "arroz blanco", "arroz cocido"],
            "channel_terms": [],
            "use_context": [],
            "strategy": [],
            "attributes": [],
        })
        text = build_semantic_text(p)
        assert "arrocito" in text
        assert "arroz blanco" in text

    def test_semantic_tags_channel_terms_included(self):
        from app.services.embedding_service import build_semantic_text
        p = _make_rich_product(semantic_tags={
            "synonyms": [],
            "channel_terms": ["mayorista", "tendero", "distribuidor"],
            "use_context": [],
            "strategy": [],
            "attributes": [],
        })
        text = build_semantic_text(p)
        assert "mayorista" in text

    def test_semantic_tags_strategy_included(self):
        from app.services.embedding_service import build_semantic_text
        p = _make_rich_product(semantic_tags={
            "synonyms": [],
            "channel_terms": [],
            "use_context": [],
            "strategy": ["producto ancla", "alta rotacion"],
            "attributes": [],
        })
        text = build_semantic_text(p)
        assert "producto ancla" in text

    def test_returns_string(self):
        from app.services.embedding_service import build_semantic_text
        p = _make_rich_product()
        assert isinstance(build_semantic_text(p), str)

    def test_parts_joined_with_period(self):
        """Las partes se unen con '. ' — facilita la tokenizacion del modelo."""
        from app.services.embedding_service import build_semantic_text
        p = _make_rich_product()
        text = build_semantic_text(p)
        assert ". " in text


# ── generate_embedding ───────────────────────────────────────────────────

class TestGenerateEmbedding:

    @pytest.fixture(autouse=True)
    def patch_voyage_client(self):
        """Reemplaza el cliente Voyage AI por un mock."""
        mock_result = MagicMock()
        mock_result.embeddings = [[0.1] * 1024]
        mock_client = AsyncMock()
        mock_client.embed = AsyncMock(return_value=mock_result)
        with patch("app.services.embedding_service._voyage_client", mock_client):
            self.mock_client = mock_client
            yield

    async def test_returns_list_of_floats(self):
        from app.services.embedding_service import generate_embedding
        result = await generate_embedding("texto de prueba")
        assert isinstance(result, list)
        assert len(result) == 1024

    async def test_calls_voyage_with_correct_model(self):
        from app.services.embedding_service import generate_embedding
        await generate_embedding("texto")
        self.mock_client.embed.assert_called_once()
        call_kwargs = self.mock_client.embed.call_args
        assert call_kwargs.kwargs.get("model") == "voyage-3" or \
               (call_kwargs.args and "voyage-3" in str(call_kwargs))

    async def test_retries_on_failure(self):
        """En caso de fallo, debe reintentar hasta 3 veces."""
        from app.services.embedding_service import generate_embedding
        mock_result = MagicMock()
        mock_result.embeddings = [[0.5] * 1024]
        self.mock_client.embed = AsyncMock(
            side_effect=[Exception("timeout"), Exception("timeout"), mock_result]
        )
        # El tercer intento tiene exito; pero embed retorna mock_result no la lista
        # Ajustar para que el tercer intento sea un return_value correcto:
        self.mock_client.embed = AsyncMock(
            side_effect=[Exception("rate_limit"), mock_result]
        )
        result = await generate_embedding("texto")
        assert len(result) == 1024
        assert self.mock_client.embed.call_count == 2

    async def test_raises_after_all_retries_fail(self):
        """Si los 3 intentos fallan, debe propagar la excepcion."""
        from app.services.embedding_service import generate_embedding
        self.mock_client.embed = AsyncMock(side_effect=Exception("servicio caido"))
        with pytest.raises(Exception, match="servicio caido"):
            await generate_embedding("texto")


# ── search_products ───────────────────────────────────────────────────────

class TestSearchProducts:
    """
    search_products llama a generate_embedding y luego a la BD.
    Mockeamos ambas capas para verificar que los filtros se aplican correctamente.
    """

    @pytest.fixture(autouse=True)
    def patch_dependencies(self, make_product):
        """Parchea generate_embedding y la sesion de BD."""
        self.mock_product = make_product()
        self.fake_embedding = [0.1] * 1024

        # Mock generate_embedding
        self.gen_emb_patch = patch(
            "app.services.embedding_service.generate_embedding",
            new=AsyncMock(return_value=self.fake_embedding),
        )

        # Mock sesion BD: scalars().all() retorna una lista de productos
        self.mock_scalars = MagicMock()
        self.mock_scalars.all = MagicMock(return_value=[self.mock_product])
        mock_execute_result = MagicMock()
        mock_execute_result.scalars = MagicMock(return_value=self.mock_scalars)

        self.mock_db = AsyncMock()
        self.mock_db.execute = AsyncMock(return_value=mock_execute_result)

        self.gen_emb_patch.start()
        yield
        self.gen_emb_patch.stop()

    async def test_returns_list(self):
        from app.services.embedding_service import search_products
        result = await search_products(
            query="arroz de grano largo",
            tenant_id="aaaaaaaa-0000-0000-0000-000000000001",
            db=self.mock_db,
        )
        assert isinstance(result, list)

    async def test_calls_generate_embedding(self):
        from app.services.embedding_service import search_products
        with patch("app.services.embedding_service.generate_embedding",
                   new=AsyncMock(return_value=self.fake_embedding)) as mock_gen:
            await search_products(
                query="arroz",
                tenant_id="aaaaaaaa-0000-0000-0000-000000000001",
                db=self.mock_db,
            )
            mock_gen.assert_called_once_with("arroz")

    async def test_calls_db_execute(self):
        from app.services.embedding_service import search_products
        await search_products(
            query="detergente",
            tenant_id="aaaaaaaa-0000-0000-0000-000000000001",
            db=self.mock_db,
        )
        self.mock_db.execute.assert_called_once()

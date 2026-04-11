"""
Tests de app.core.crypto — encriptacion simetrica Fernet.

Cubre:
  - Round-trip encrypt → decrypt
  - Tolerancia a valores legacy (texto plano sin encriptar)
  - Manejo de string vacio / None
  - Distintos valores producen tokens distintos (no determinista por timestamp)
  - El token encriptado es distinto al texto original
"""
import pytest
from unittest.mock import patch
from cryptography.fernet import Fernet


@pytest.fixture(autouse=True)
def patch_encryption_key(fernet_key):
    """Sustituye la llave de settings por una llave Fernet valida de prueba."""
    with patch("app.core.crypto.settings") as mock_settings:
        mock_settings.encryption_key = fernet_key
        yield mock_settings


class TestEncryptValue:

    def test_returns_string(self):
        from app.core.crypto import encrypt_value
        result = encrypt_value("hola_mundo")
        assert isinstance(result, str)

    def test_token_different_from_plaintext(self):
        from app.core.crypto import encrypt_value
        plaintext = "EAABsbCS...token_whatsapp"
        token = encrypt_value(plaintext)
        assert token != plaintext

    def test_token_starts_with_gAAAAA(self):
        """Los tokens Fernet siempre empiezan con 'gAAAAA' (base64 del header)."""
        from app.core.crypto import encrypt_value
        token = encrypt_value("cualquier_valor")
        assert token.startswith("gAAAAA"), f"Token inesperado: {token[:20]}"

    def test_same_input_produces_different_tokens(self):
        """Fernet incluye timestamp + nonce: el mismo plaintext produce tokens distintos."""
        from app.core.crypto import encrypt_value
        t1 = encrypt_value("mismo_valor")
        t2 = encrypt_value("mismo_valor")
        assert t1 != t2


class TestDecryptValue:

    def test_round_trip(self):
        """encrypt → decrypt debe retornar el valor original."""
        from app.core.crypto import encrypt_value, decrypt_value
        original = "EAABsbCS1234567890abcdef"
        assert decrypt_value(encrypt_value(original)) == original

    def test_legacy_plaintext_tolerance(self):
        """
        Si el valor no es un token Fernet valido (legacy sin encriptar),
        decrypt_value debe retornar el texto tal como esta.
        """
        from app.core.crypto import decrypt_value
        legacy_token = "EAABsbCS_sin_encriptar_legacy"
        result = decrypt_value(legacy_token)
        assert result == legacy_token

    def test_empty_string_returns_empty(self):
        from app.core.crypto import decrypt_value
        assert decrypt_value("") == ""

    def test_whitespace_tolerance(self):
        """Un valor de solo espacios (legacy) se retorna sin modificar."""
        from app.core.crypto import decrypt_value
        assert decrypt_value("   ") == "   "

    def test_decrypt_with_wrong_key_returns_original(self, fernet_key):
        """
        Si se desencripta con una llave diferente a la que encripto,
        decrypt_value debe retornar el token original (tolerancia legacy).
        """
        from app.core.crypto import encrypt_value, decrypt_value
        token = encrypt_value("valor_secreto")

        # Cambiar la llave por una diferente
        different_key = Fernet.generate_key().decode()
        with patch("app.core.crypto.settings") as mock_settings:
            mock_settings.encryption_key = different_key
            result = decrypt_value(token)

        # Con llave incorrecta, actua como legacy: retorna el token sin descifrar
        assert result == token

    def test_unicode_values(self):
        """Valores con caracteres especiales y tildes deben round-trip correctamente."""
        from app.core.crypto import encrypt_value, decrypt_value
        original = "Distribuciones La Garantía — Magangué 🇨🇴"
        assert decrypt_value(encrypt_value(original)) == original

    def test_long_token(self):
        """Tokens largos tipicos de WhatsApp Business API (> 200 chars)."""
        from app.core.crypto import encrypt_value, decrypt_value
        original = "EAABsbCS" + "x" * 200
        assert decrypt_value(encrypt_value(original)) == original


class TestEncryptDecryptNone:

    def test_none_like_empty_string(self):
        """
        decrypt_value recibe siempre str; si viene string vacio retorna vacio.
        Este test documenta el comportamiento esperado (no lanza excepcion).
        """
        from app.core.crypto import decrypt_value
        result = decrypt_value("")
        assert result == ""

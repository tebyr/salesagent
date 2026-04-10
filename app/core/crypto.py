"""
Utilidades de encripcion simetrica para valores sensibles en BD.

Usa Fernet (AES-128-CBC + HMAC-SHA256) de la libreria `cryptography`.
La llave vive exclusivamente en la variable de entorno ENCRYPTION_KEY
y nunca se persiste en la base de datos.

Generacion de la llave (ejecutar una sola vez):
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

Resistencia a tokens legacy:
    decrypt_value es tolerante: si el valor no es un token Fernet valido
    (ej. tokens guardados antes de activar la encripcion) retorna el texto
    original sin error, permitiendo una migracion gradual sin downtime.
"""
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def _fernet() -> Fernet:
    """Instancia Fernet con la llave configurada."""
    return Fernet(settings.encryption_key.encode())


def encrypt_value(plaintext: str) -> str:
    """
    Encripta un valor de texto plano y retorna el token Fernet como string.

    Args:
        plaintext: Valor a encriptar (ej. access_token de WhatsApp).

    Returns:
        Token Fernet en formato base64 URL-safe (siempre empieza con 'gAAAAA').
    """
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str:
    """
    Desencripta un token Fernet y retorna el texto original.

    Tolerante a valores legacy (texto plano): si el valor no es un token
    Fernet valido, retorna el valor tal como esta sin lanzar excepcion.
    Esto permite convivencia entre tokens ya encriptados y tokens guardados
    antes de activar la encripcion, sin necesidad de migracion de datos.

    Args:
        ciphertext: Token Fernet o texto plano (legacy).

    Returns:
        Texto desencriptado, o el valor original si no es un token valido.
    """
    if not ciphertext:
        return ciphertext
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except (InvalidToken, Exception):
        # Valor legacy sin encriptar — retornar tal cual
        return ciphertext

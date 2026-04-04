"""
Modelo base con campos comunes para todos los modelos.
"""
from sqlalchemy import Column, DateTime, func, UUID
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from app.core.database import Base
import uuid


class TimestampMixin:
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class UUIDMixin:
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

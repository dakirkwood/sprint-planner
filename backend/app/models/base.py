# app/models/base.py
"""
Base SQLAlchemy model class with common mixins and utilities.
"""
from datetime import datetime
from uuid import uuid4, UUID
from sqlalchemy import DateTime, func, String, TypeDecorator
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from typing import Any


class GUIDString(TypeDecorator):
    """Platform-independent GUID type using String storage."""
    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return str(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return UUID(value)
        return value


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    # Type annotation for type hints support
    type_annotation_map = {
        datetime: DateTime(timezone=True),
    }


class TimestampMixin:
    """Mixin that adds created_at and updated_at columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )


class UUIDMixin:
    """Mixin that adds UUID primary key."""

    id: Mapped[Any] = mapped_column(
        GUIDString(),
        primary_key=True,
        default=uuid4
    )

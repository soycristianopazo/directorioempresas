"""Notificaciones in-app, preferencias y envíos por canal (fase 7.9)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Text, text
from sqlalchemy.dialects.postgresql import ENUM, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

NotificationPriorityEnum = ENUM(
    "LOW",
    "NORMAL",
    "HIGH",
    name="notification_priority",
    schema="app",
    create_type=False,
)
NotificationChannelEnum = ENUM(
    "IN_APP", "EMAIL", name="notification_channel", schema="app", create_type=False
)
NotificationDeliveryStatusEnum = ENUM(
    "PENDING",
    "SENT",
    "FAILED",
    name="notification_delivery_status",
    schema="app",
    create_type=False,
)


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    recipient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE")
    )

    type: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    entity_type: Mapped[str | None] = mapped_column(Text)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    action_url: Mapped[str | None] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(
        NotificationPriorityEnum, nullable=False, server_default="NORMAL"
    )

    read_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE")
    )

    channel: Mapped[str] = mapped_column(NotificationChannelEnum, nullable=False)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(nullable=False, server_default=text("true"))


class NotificationDelivery(Base):
    __tablename__ = "notification_deliveries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    notification_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("notifications.id", ondelete="CASCADE")
    )

    channel: Mapped[str] = mapped_column(NotificationChannelEnum, nullable=False)
    status: Mapped[str] = mapped_column(
        NotificationDeliveryStatusEnum, nullable=False, server_default="PENDING"
    )
    provider_message_id: Mapped[str | None] = mapped_column(Text)
    attempted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)

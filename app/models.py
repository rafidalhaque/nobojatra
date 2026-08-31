from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import (
    Boolean,
    Computed,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

UNIT_TYPE = Enum("branch", "dept", name="unit_type")
POST_STATUS = Enum("draft", "published", name="post_status")
NOTIF_STATUS = Enum("read", "unread", name="notif_status")
THEME = Enum("light", "dark", name="theme_pref")
LANG = Enum("en", "bn", name="lang_pref")


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )


def _created_at() -> Mapped[dt.datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Area(Base):
    __tablename__ = "areas"
    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    created_at: Mapped[dt.datetime] = _created_at()


class OrgUnit(Base):
    __tablename__ = "org_units"
    id: Mapped[uuid.UUID] = _uuid_pk()
    unit_type: Mapped[str] = mapped_column(UNIT_TYPE, nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    code: Mapped[str] = mapped_column(String(120), nullable=False)
    area_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("areas.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[dt.datetime] = _created_at()
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    area: Mapped[Area] = relationship(lazy="joined")
    __table_args__ = (UniqueConstraint("unit_type", "code", name="uq_org_unit_type_code"),)


class Account(Base):
    __tablename__ = "accounts"
    id: Mapped[uuid.UUID] = _uuid_pk()
    org_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("org_units.id", ondelete="CASCADE"), nullable=True
    )
    username: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    is_super_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    theme_pref: Mapped[str] = mapped_column(THEME, server_default="light", nullable=False)
    lang_pref: Mapped[str] = mapped_column(LANG, server_default="en", nullable=False)
    created_at: Mapped[dt.datetime] = _created_at()
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    org_unit: Mapped[OrgUnit | None] = relationship(lazy="joined")


class Permission(Base):
    __tablename__ = "permissions"
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)


class PermissionProfile(Base):
    __tablename__ = "permission_profiles"
    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)  # dept_default | branch_default


class ProfilePermission(Base):
    __tablename__ = "profile_permissions"
    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("permission_profiles.id", ondelete="CASCADE"), primary_key=True
    )
    permission_key: Mapped[str] = mapped_column(
        ForeignKey("permissions.key", ondelete="CASCADE"), primary_key=True
    )
    allowed: Mapped[bool] = mapped_column(Boolean, nullable=False)


class OrgUnitPermission(Base):
    """Per-unit override on top of the profile default. Absent row = inherit."""

    __tablename__ = "org_unit_permissions"
    org_unit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("org_units.id", ondelete="CASCADE"), primary_key=True
    )
    permission_key: Mapped[str] = mapped_column(
        ForeignKey("permissions.key", ondelete="CASCADE"), primary_key=True
    )
    allowed: Mapped[bool] = mapped_column(Boolean, nullable=False)


class Category(Base):
    __tablename__ = "categories"
    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    created_at: Mapped[dt.datetime] = _created_at()


class Post(Base):
    __tablename__ = "posts"
    id: Mapped[uuid.UUID] = _uuid_pk()
    org_unit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("org_units.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(POST_STATUS, server_default="draft", nullable=False, index=True)
    # User-fillable. Falls back to now() at insert when omitted (handled in router).
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    published_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    search_tsv: Mapped[str] = mapped_column(
        TSVECTOR,
        Computed(
            "to_tsvector('simple', coalesce(title,'') || ' ' || coalesce(body,''))",
            persisted=True,
        ),
    )
    media: Mapped[list[PostMedia]] = relationship(
        back_populates="post", cascade="all, delete-orphan", lazy="selectin", order_by="PostMedia.sort_order"
    )


class PostMedia(Base):
    __tablename__ = "post_media"
    id: Mapped[uuid.UUID] = _uuid_pk()
    post_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    s3_key: Mapped[str] = mapped_column(Text, nullable=False)
    original_filename: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[dt.datetime] = _created_at()
    post: Mapped[Post] = relationship(back_populates="media")


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[uuid.UUID] = _uuid_pk()
    sender_org_unit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("org_units.id", ondelete="CASCADE"), nullable=False, index=True
    )
    recipient_org_unit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("org_units.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Audit only. NEVER serialized to any response.
    sender_account_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[dt.datetime] = _created_at()
    read_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[uuid.UUID] = _uuid_pk()
    recipient_org_unit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("org_units.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    source_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    status: Mapped[str] = mapped_column(NOTIF_STATUS, server_default="unread", nullable=False, index=True)
    created_at: Mapped[dt.datetime] = _created_at()
    read_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

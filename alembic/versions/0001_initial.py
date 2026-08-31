"""initial schema + RLS + permission seed

Revision ID: 0001
Revises:
Create Date: 2026-08-31
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.config import get_settings
from app.permissions import CATALOG, PROFILE_DEFAULTS

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

unit_type = postgresql.ENUM("branch", "dept", name="unit_type")
post_status = postgresql.ENUM("draft", "published", name="post_status")
notif_status = postgresql.ENUM("read", "unread", name="notif_status")
theme_pref = postgresql.ENUM("light", "dark", name="theme_pref")
lang_pref = postgresql.ENUM("en", "bn", name="lang_pref")

_ts = sa.text("now()")


def _uuid_col():
    return sa.Column(
        "id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    )


def upgrade() -> None:
    bind = op.get_bind()
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    for e in (unit_type, post_status, notif_status, theme_pref, lang_pref):
        e.create(bind, checkfirst=True)

    op.create_table(
        "areas",
        _uuid_col(),
        sa.Column("name", sa.String(200), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_ts, nullable=False),
    )

    op.create_table(
        "org_units",
        _uuid_col(),
        sa.Column("unit_type", unit_type, nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("code", sa.String(120), nullable=False),
        sa.Column("area_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("areas.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_ts, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_ts, nullable=False),
        sa.UniqueConstraint("unit_type", "code", name="uq_org_unit_type_code"),
    )

    op.create_table(
        "accounts",
        _uuid_col(),
        sa.Column("org_unit_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("org_units.id", ondelete="CASCADE"), nullable=True),
        sa.Column("username", sa.String(150), nullable=False, unique=True),
        sa.Column("password_hash", sa.Text, nullable=False),
        sa.Column("is_super_admin", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("theme_pref", theme_pref, nullable=False, server_default="light"),
        sa.Column("lang_pref", lang_pref, nullable=False, server_default="en"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_ts, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_ts, nullable=False),
    )

    op.create_table(
        "permissions",
        sa.Column("key", sa.String(80), primary_key=True),
        sa.Column("description", sa.Text, nullable=False),
    )
    op.create_table(
        "permission_profiles",
        _uuid_col(),
        sa.Column("name", sa.String(50), nullable=False, unique=True),
    )
    op.create_table(
        "profile_permissions",
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("permission_profiles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("permission_key", sa.String(80), sa.ForeignKey("permissions.key", ondelete="CASCADE"), primary_key=True),
        sa.Column("allowed", sa.Boolean, nullable=False),
    )
    op.create_table(
        "org_unit_permissions",
        sa.Column("org_unit_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("org_units.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("permission_key", sa.String(80), sa.ForeignKey("permissions.key", ondelete="CASCADE"), primary_key=True),
        sa.Column("allowed", sa.Boolean, nullable=False),
    )

    op.create_table(
        "categories",
        _uuid_col(),
        sa.Column("name", sa.String(150), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_ts, nullable=False),
    )

    op.create_table(
        "posts",
        _uuid_col(),
        sa.Column("org_unit_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("org_units.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("body", sa.Text, nullable=False, server_default=""),
        sa.Column("status", post_status, nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_ts, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_ts, nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "search_tsv",
            postgresql.TSVECTOR,
            sa.Computed("to_tsvector('simple', coalesce(title,'') || ' ' || coalesce(body,''))", persisted=True),
        ),
    )
    op.create_index("ix_posts_org_unit_id", "posts", ["org_unit_id"])
    op.create_index("ix_posts_category_id", "posts", ["category_id"])
    op.create_index("ix_posts_status", "posts", ["status"])
    op.create_index("ix_posts_created_at", "posts", ["created_at"])
    op.create_index("ix_posts_search_tsv", "posts", ["search_tsv"], postgresql_using="gin")

    op.create_table(
        "post_media",
        _uuid_col(),
        sa.Column("post_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("posts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("s3_key", sa.Text, nullable=False),
        sa.Column("original_filename", sa.Text, nullable=False),
        sa.Column("content_type", sa.Text, nullable=True),
        sa.Column("size_bytes", sa.Integer, nullable=False, server_default="0"),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_ts, nullable=False),
    )
    op.create_index("ix_post_media_post_id", "post_media", ["post_id"])

    op.create_table(
        "messages",
        _uuid_col(),
        sa.Column("sender_org_unit_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("org_units.id", ondelete="CASCADE"), nullable=False),
        sa.Column("recipient_org_unit_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("org_units.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sender_account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_ts, nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_messages_sender", "messages", ["sender_org_unit_id"])
    op.create_index("ix_messages_recipient", "messages", ["recipient_org_unit_id"])

    op.create_table(
        "notifications",
        _uuid_col(),
        sa.Column("recipient_org_unit_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("org_units.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("body", sa.Text, nullable=False, server_default=""),
        sa.Column("source_type", sa.String(50), nullable=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", notif_status, nullable=False, server_default="unread"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_ts, nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_notifications_recipient", "notifications", ["recipient_org_unit_id"])
    op.create_index("ix_notifications_status", "notifications", ["status"])

    # ---- Row-Level Security (spec 11.3) --------------------------------------
    cur_ou = "nullif(current_setting('app.current_org_unit', true), '')::uuid"
    is_sa = "current_setting('app.is_super_admin', true) = 'on'"

    op.execute("ALTER TABLE posts ENABLE ROW LEVEL SECURITY")
    op.execute(f"""
        CREATE POLICY posts_select ON posts FOR SELECT
        USING ({is_sa} OR status = 'published' OR org_unit_id = {cur_ou})
    """)
    op.execute(f"""
        CREATE POLICY posts_write ON posts FOR ALL
        USING ({is_sa} OR org_unit_id = {cur_ou})
        WITH CHECK ({is_sa} OR org_unit_id = {cur_ou})
    """)

    op.execute("ALTER TABLE messages ENABLE ROW LEVEL SECURITY")
    op.execute(f"""
        CREATE POLICY messages_rw ON messages FOR ALL
        USING ({is_sa} OR sender_org_unit_id = {cur_ou} OR recipient_org_unit_id = {cur_ou})
        WITH CHECK ({is_sa} OR sender_org_unit_id = {cur_ou})
    """)

    op.execute("ALTER TABLE notifications ENABLE ROW LEVEL SECURITY")
    op.execute(f"""
        CREATE POLICY notifications_rw ON notifications FOR ALL
        USING ({is_sa} OR recipient_org_unit_id = {cur_ou})
        WITH CHECK ({is_sa} OR recipient_org_unit_id = {cur_ou})
    """)

    # post_media has no RLS: every read path first loads the parent post, which
    # IS RLS-guarded (see routers/posts.py get_media).

    # ---- GRANTs to the runtime app role -----------------------------------
    app_user = get_settings().app_db_user
    op.execute(f"GRANT USAGE ON SCHEMA public TO {app_user}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {app_user}")
    op.execute(f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {app_user}")
    op.execute(
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {app_user}"
    )

    # ---- Seed permission catalog + two role defaults (spec 15) -------------
    op.bulk_insert(
        sa.table("permissions", sa.column("key", sa.String), sa.column("description", sa.Text)),
        [{"key": k, "description": v} for k, v in CATALOG.items()],
    )
    profiles = sa.table("permission_profiles", sa.column("id", postgresql.UUID), sa.column("name", sa.String))
    op.bulk_insert(profiles, [{"name": "dept_default"}, {"name": "branch_default"}])
    for pname, mapping in PROFILE_DEFAULTS.items():
        for key, allowed in mapping.items():
            op.execute(
                "INSERT INTO profile_permissions (profile_id, permission_key, allowed) "
                f"SELECT id, '{key}', {str(bool(allowed)).lower()} "
                f"FROM permission_profiles WHERE name = '{pname}'"
            )


def downgrade() -> None:
    for t in (
        "notifications", "messages", "post_media", "posts", "categories",
        "org_unit_permissions", "profile_permissions", "permission_profiles",
        "permissions", "accounts", "org_units", "areas",
    ):
        op.execute(f"DROP TABLE IF EXISTS {t} CASCADE")
    for e in ("unit_type", "post_status", "notif_status", "theme_pref", "lang_pref"):
        op.execute(f"DROP TYPE IF EXISTS {e}")

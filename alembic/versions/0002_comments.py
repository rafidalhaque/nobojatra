"""comments per post

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-11
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

_ts = sa.text("now()")


def upgrade() -> None:
    op.create_table(
        "comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("post_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("posts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_unit_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("org_units.id", ondelete="CASCADE"), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_ts, nullable=False),
    )
    op.create_index("ix_comments_post_id", "comments", ["post_id"])
    op.create_index("ix_comments_org_unit_id", "comments", ["org_unit_id"])

    # ---- Row-Level Security, mirroring posts' visibility rules ---------------
    cur_ou = "nullif(current_setting('app.current_org_unit', true), '')::uuid"
    is_sa = "current_setting('app.is_super_admin', true) = 'on'"
    post_visible = (
        "EXISTS (SELECT 1 FROM posts p WHERE p.id = comments.post_id "
        f"AND (p.status = 'published' OR p.org_unit_id = {cur_ou}))"
    )

    op.execute("ALTER TABLE comments ENABLE ROW LEVEL SECURITY")
    op.execute(f"""
        CREATE POLICY comments_select ON comments FOR SELECT
        USING ({is_sa} OR {post_visible})
    """)
    op.execute(f"""
        CREATE POLICY comments_insert ON comments FOR INSERT
        WITH CHECK ({is_sa} OR (org_unit_id = {cur_ou} AND {post_visible}))
    """)
    op.execute(f"""
        CREATE POLICY comments_delete ON comments FOR DELETE
        USING ({is_sa} OR org_unit_id = {cur_ou})
    """)

    from app.config import get_settings

    app_user = get_settings().app_db_user
    op.execute(f"GRANT SELECT, INSERT, DELETE ON comments TO {app_user}")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS comments CASCADE")

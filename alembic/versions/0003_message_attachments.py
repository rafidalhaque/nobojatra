"""file attachments on messages

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-11
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

_ts = sa.text("now()")


def upgrade() -> None:
    op.create_table(
        "message_attachments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("messages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("s3_key", sa.Text, nullable=False),
        sa.Column("original_filename", sa.Text, nullable=False),
        sa.Column("content_type", sa.Text, nullable=True),
        sa.Column("size_bytes", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_ts, nullable=False),
    )
    op.create_index("ix_message_attachments_message_id", "message_attachments", ["message_id"])

    # No RLS: every read path first loads the parent message, which IS
    # RLS-guarded (see routers/messages.py get_attachment) — mirrors post_media.
    from app.config import get_settings

    app_user = get_settings().app_db_user
    op.execute(f"GRANT SELECT, INSERT, DELETE ON message_attachments TO {app_user}")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS message_attachments CASCADE")

"""Create analysis records table

Revision ID: 66cbf0fe8d26
Revises:
Create Date: 2026-02-15 16:10:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "66cbf0fe8d26"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "analysis_records",
        sa.Column("analysis_id", sa.String(length=64), nullable=False),
        sa.Column("content_type", sa.String(length=16), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("input_size", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=512), nullable=True),
        sa.PrimaryKeyConstraint("analysis_id"),
    )
    op.create_index(
        op.f("ix_analysis_records_content_hash"),
        "analysis_records",
        ["content_hash"],
        unique=False,
    )
    op.create_index(
        op.f("ix_analysis_records_content_type"),
        "analysis_records",
        ["content_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_analysis_records_created_at"),
        "analysis_records",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_analysis_records_source"),
        "analysis_records",
        ["source"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_analysis_records_source"), table_name="analysis_records")
    op.drop_index(op.f("ix_analysis_records_created_at"), table_name="analysis_records")
    op.drop_index(op.f("ix_analysis_records_content_type"), table_name="analysis_records")
    op.drop_index(op.f("ix_analysis_records_content_hash"), table_name="analysis_records")
    op.drop_table("analysis_records")

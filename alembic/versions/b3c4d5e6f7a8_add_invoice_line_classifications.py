"""add invoice_line_classifications table

Revision ID: b3c4d5e6f7a8
Revises: 2eea1d1a42ba
Create Date: 2026-04-04 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3c4d5e6f7a8"
down_revision: Union[str, Sequence[str], None] = "2eea1d1a42ba"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create invoice_line_classifications table."""
    op.create_table(
        "invoice_line_classifications",
        sa.Column("id", sa.BIGINT(), sa.Identity(always=True), primary_key=True),
        sa.Column(
            "invoice_id",
            sa.BIGINT(),
            sa.ForeignKey("invoices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("line_index", sa.SmallInteger(), nullable=False),
        sa.Column("p7_text", sa.Text(), nullable=False),
        sa.Column("verdict", sa.String(30), nullable=False),
        sa.Column("rate_percent", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("pkwiu_code", sa.String(20), nullable=True),
        sa.Column("pkwiu_description", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column("ambiguity_flags", postgresql.JSONB(), nullable=True),
        sa.Column("clarification_question", sa.Text(), nullable=True),
        sa.Column("corridor", sa.String(20), nullable=True),
        sa.Column("llm_calls_count", sa.SmallInteger(), server_default="0"),
        sa.Column(
            "classified_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("invoice_id", "line_index", name="uq_invoice_line"),
    )
    op.create_index(
        "ix_invoice_line_classifications_invoice_id",
        "invoice_line_classifications",
        ["invoice_id"],
    )


def downgrade() -> None:
    """Drop invoice_line_classifications table."""
    op.drop_index(
        "ix_invoice_line_classifications_invoice_id",
        table_name="invoice_line_classifications",
    )
    op.drop_table("invoice_line_classifications")

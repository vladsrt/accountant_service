"""add buyer_nip and xml_raw to invoices

Revision ID: a1b2c3d4e5f6
Revises: c394c8591868
Create Date: 2026-03-28 23:50:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "c394c8591868"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add buyer_nip and xml_raw columns to the invoices table."""
    op.add_column("invoices", sa.Column("buyer_nip", sa.String(length=10), nullable=True))
    op.add_column("invoices", sa.Column("xml_raw", sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove buyer_nip and xml_raw columns from the invoices table."""
    op.drop_column("invoices", "xml_raw")
    op.drop_column("invoices", "buyer_nip")

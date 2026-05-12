"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-05-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("store", sa.String(length=100), nullable=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=10), server_default="ARS", nullable=True),
        sa.Column(
            "url",
            sa.Text(),
            nullable=True,
            comment="Unique product URL used by the scraper upsert.",
        ),
        sa.Column(
            "scraped_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_products"),
        sa.UniqueConstraint("url", name="uq_products_url"),
    )
    op.create_index("ix_products_store", "products", ["store"])
    op.create_index("ix_products_price", "products", ["price"])
    op.create_index("ix_products_scraped_at", "products", ["scraped_at"])

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("username", sa.String(length=150), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("username", name="uq_users_username"),
    )


def downgrade() -> None:
    op.drop_table("users")
    op.drop_index("ix_products_scraped_at", table_name="products")
    op.drop_index("ix_products_price", table_name="products")
    op.drop_index("ix_products_store", table_name="products")
    op.drop_table("products")

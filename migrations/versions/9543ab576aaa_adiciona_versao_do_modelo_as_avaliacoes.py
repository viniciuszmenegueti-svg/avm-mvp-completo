"""adiciona versão do modelo às avaliações

Revision ID: 9543ab576aaa
Revises: 5053c3aae8b1
Create Date: 2026-07-23 17:28:22.093505

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "9543ab576aaa"
down_revision: Union[str, Sequence[str], None] = "5053c3aae8b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Adiciona e preenche a versão do modelo das avaliações."""
    op.add_column(
        "valuations",
        sa.Column(
            "model_version",
            sa.String(length=50),
            nullable=True,
        ),
    )

    op.execute(
        sa.text(
            """
            UPDATE valuations
            SET model_version = '1.0.0'
            WHERE model_version IS NULL
              AND method = 'RULE_BASED_V1'
            """
        )
    )

    connection = op.get_bind()

    missing_versions = connection.scalar(
        sa.text(
            """
            SELECT COUNT(*)
            FROM valuations
            WHERE model_version IS NULL
            """
        )
    )

    if missing_versions:
        raise RuntimeError("Existem avaliações sem versão de modelo compatível.")

    op.alter_column(
        "valuations",
        "model_version",
        existing_type=sa.String(length=50),
        nullable=False,
    )


def downgrade() -> None:
    """Remove a versão do modelo das avaliações."""
    op.drop_column(
        "valuations",
        "model_version",
    )

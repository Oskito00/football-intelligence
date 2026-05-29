"""Ensure Football Data Status competition lookup table exists.

Revision ID: 0002_team_main_competition
Revises: 0001_baseline_schema
Create Date: 2026-05-29
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "0002_team_main_competition"
down_revision: Union[str, None] = "0001_baseline_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS team_main_competition (
            team_id integer NOT NULL,
            team_name text,
            main_competition_id integer,
            main_competition_name text,
            main_competition_country text,
            match_count integer,
            CONSTRAINT team_main_competition_pkey PRIMARY KEY (team_id)
        )
        """
    )


def downgrade() -> None:
    op.drop_table("team_main_competition")

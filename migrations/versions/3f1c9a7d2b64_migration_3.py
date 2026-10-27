"""migration - 3

- rename misspelled table waether_observations -> weather_observations
- add weather_observations.is_forecast
- fix users.name server default (was the SQL keyword USER, i.e. the DB role name)

Revision ID: 3f1c9a7d2b64
Revises: 0975033808d9
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "3f1c9a7d2b64"
down_revision: Union[str, Sequence[str], None] = "0975033808d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())

    if "waether_observations" in tables and "weather_observations" not in tables:
        op.rename_table("waether_observations", "weather_observations")
        op.execute("ALTER INDEX IF EXISTS ix_waether_observations_observed_at "
                   "RENAME TO ix_weather_observations_observed_at")
        tables = set(sa.inspect(bind).get_table_names())

    if "weather_observations" in tables:
        columns = {c["name"] for c in sa.inspect(bind).get_columns("weather_observations")}
        if "is_forecast" not in columns:
            op.add_column("weather_observations",
                          sa.Column("is_forecast", sa.Boolean(), server_default=sa.text("false"), nullable=False))

    op.alter_column("users", "name", existing_type=sa.String(length=120), server_default=sa.text("'User'"))
    # Existing accounts got the DB role name as their name; use the email prefix instead.
    op.execute("UPDATE users SET name = split_part(email, '@', 1) WHERE name = current_user")


def downgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "weather_observations" in tables:
        op.drop_column("weather_observations", "is_forecast")
        op.rename_table("weather_observations", "waether_observations")

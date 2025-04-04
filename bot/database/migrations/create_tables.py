"""create tables

Revision ID: 001
Revises:
Create Date: 2024-03-20 10:00:00.000000

"""

from datetime import datetime

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Создаем таблицу users
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=32), nullable=True),
        sa.Column("first_name", sa.String(length=64), nullable=True),
        sa.Column("last_name", sa.String(length=64), nullable=True),
        sa.Column(
            "registration_date", sa.DateTime(), nullable=False, default=datetime.utcnow
        ),
        sa.Column(
            "last_active", sa.DateTime(), nullable=False, default=datetime.utcnow
        ),
        sa.Column("current_investigation_id", sa.Integer(), nullable=True),
        sa.Column("energy", sa.Integer(), nullable=False, default=100),
        sa.Column("max_energy", sa.Integer(), nullable=False, default=100),
        sa.Column(
            "last_energy_update", sa.DateTime(), nullable=False, default=datetime.utcnow
        ),
        sa.Column("level", sa.Integer(), nullable=False, default=1),
        sa.Column("experience", sa.Integer(), nullable=False, default=0),
        sa.Column("detective_skill", sa.Integer(), nullable=False, default=1),
        sa.Column("forensic_skill", sa.Integer(), nullable=False, default=1),
        sa.Column("psychology_skill", sa.Integer(), nullable=False, default=1),
        sa.Column("stats", postgresql.JSONB(), nullable=False, default={}),
        sa.Column("settings", postgresql.JSONB(), nullable=False, default={}),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("telegram_id"),
        sa.CheckConstraint("energy >= 0 AND energy <= max_energy"),
        sa.CheckConstraint("level >= 1"),
        sa.CheckConstraint("experience >= 0"),
        sa.CheckConstraint("detective_skill >= 1 AND detective_skill <= 100"),
        sa.CheckConstraint("forensic_skill >= 1 AND forensic_skill <= 100"),
        sa.CheckConstraint("psychology_skill >= 1 AND psychology_skill <= 100"),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"])
    op.create_index("ix_users_level", "users", ["level"])
    op.create_index("ix_users_experience", "users", ["experience"])

    # Создаем таблицу investigations
    op.create_table(
        "investigations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, default="active"),
        sa.Column("difficulty", sa.String(length=20), nullable=False),
        sa.Column("current_location", sa.String(length=64), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column(
            "last_updated", sa.DateTime(), nullable=False, default=datetime.utcnow
        ),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("evidence", postgresql.JSONB(), nullable=False, default=[]),
        sa.Column("suspects", postgresql.JSONB(), nullable=False, default=[]),
        sa.Column("locations", postgresql.JSONB(), nullable=False, default=[]),
        sa.Column("player_actions", postgresql.JSONB(), nullable=False, default=[]),
        sa.Column("progress", postgresql.JSONB(), nullable=False, default={}),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["template_id"], ["investigation_templates.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("status IN ('active', 'completed', 'failed', 'abandoned')"),
        sa.CheckConstraint("difficulty IN ('easy', 'medium', 'hard', 'expert')"),
    )
    op.create_index("ix_investigations_user_id", "investigations", ["user_id"])
    op.create_index("ix_investigations_status", "investigations", ["status"])
    op.create_index("ix_investigations_difficulty", "investigations", ["difficulty"])

    # Создаем таблицу achievements
    op.create_table(
        "achievements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("requirements", postgresql.JSONB(), nullable=False),
        sa.Column("rewards", postgresql.JSONB(), nullable=False),
        sa.Column("icon", sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        sa.CheckConstraint(
            "category IN ('investigation', 'skill', 'social', 'special')"
        ),
    )
    op.create_index("ix_achievements_category", "achievements", ["category"])

    # Создаем таблицу user_achievements
    op.create_table(
        "user_achievements",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("achievement_id", sa.Integer(), nullable=False),
        sa.Column(
            "unlocked_at", sa.DateTime(), nullable=False, default=datetime.utcnow
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["achievement_id"], ["achievements.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("user_id", "achievement_id"),
    )
    op.create_index("ix_user_achievements_user_id", "user_achievements", ["user_id"])
    op.create_index(
        "ix_user_achievements_achievement_id", "user_achievements", ["achievement_id"]
    )

    # Создаем таблицу news
    op.create_table(
        "news",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("tags", postgresql.JSONB(), nullable=False, default=[]),
        sa.Column("created_at", sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("author", sa.String(length=64), nullable=True),
        sa.Column("source", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, default="draft"),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, default={}),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "category IN ('crime', 'science', 'interview', 'tips', 'psychology', 'forensic')"
        ),
        sa.CheckConstraint("status IN ('draft', 'published', 'archived')"),
    )
    op.create_index("ix_news_category", "news", ["category"])
    op.create_index("ix_news_status", "news", ["status"])
    op.create_index("ix_news_published_at", "news", ["published_at"])
    op.create_index("ix_news_tags", "news", ["tags"], postgresql_using="gin")

    # Создаем таблицу investigation_templates
    op.create_table(
        "investigation_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("difficulty", sa.String(length=20), nullable=False),
        sa.Column("min_level", sa.Integer(), nullable=False, default=1),
        sa.Column("required_skills", postgresql.JSONB(), nullable=False, default={}),
        sa.Column("locations", postgresql.JSONB(), nullable=False, default=[]),
        sa.Column("evidence", postgresql.JSONB(), nullable=False, default=[]),
        sa.Column("suspects", postgresql.JSONB(), nullable=False, default=[]),
        sa.Column("storyline", postgresql.JSONB(), nullable=False, default=[]),
        sa.Column("solutions", postgresql.JSONB(), nullable=False, default=[]),
        sa.Column("rewards", postgresql.JSONB(), nullable=False, default={}),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("title"),
        sa.CheckConstraint("difficulty IN ('easy', 'medium', 'hard', 'expert')"),
        sa.CheckConstraint("min_level >= 1"),
    )
    op.create_index(
        "ix_investigation_templates_difficulty",
        "investigation_templates",
        ["difficulty"],
    )
    op.create_index(
        "ix_investigation_templates_min_level", "investigation_templates", ["min_level"]
    )
    op.create_index(
        "ix_investigation_templates_is_active", "investigation_templates", ["is_active"]
    )


def downgrade() -> None:
    # Удаляем таблицы в обратном порядке
    op.drop_table("user_achievements")
    op.drop_table("achievements")
    op.drop_table("news")
    op.drop_table("investigations")
    op.drop_table("investigation_templates")
    op.drop_table("users")

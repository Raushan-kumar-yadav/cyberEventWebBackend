
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    # Organizer accounts.
    op.create_table(
        "admins",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("passcode_hash", sa.String(length=255), nullable=False),
        sa.Column("session_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_admins")),
        sa.UniqueConstraint("name", name=op.f("uq_admins_name")),
    )
    # server game timer 
    game_state = op.create_table(
        "game_state",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "not_started",
                "running",
                "paused",
                "ended",
                name="gamestatus",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paused_seconds", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.CheckConstraint("id = 1", name=op.f("ck_game_state_singleton")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_game_state")),
    )
    op.bulk_insert(
        game_state, [{"id": 1, "status": "not_started", "paused_seconds": 0, "version": 0}]
    )
    # Routes to Delhi
    op.create_table(
        "paths",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("start_region", sa.String(length=64), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_paths")),
        sa.UniqueConstraint("name", name=op.f("uq_paths_name")),
    )
    # Current store prices
    op.create_table(
        "store_prices",
        sa.Column("key", sa.String(length=32), nullable=False),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("key", name=op.f("pk_store_prices")),
    )
    # Admin action  
    op.create_table(
        "admin_audit",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("admin_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("target", sa.String(length=128), nullable=True),
        sa.Column("payload", JSON_TYPE, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["admin_id"],
            ["admins.id"],
            name=op.f("fk_admin_audit_admin_id_admins"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_admin_audit")),
    )
    # final results
    op.create_table(
        "final_leaderboards",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("admin_id", sa.Integer(), nullable=True),
        sa.Column("rows", JSON_TYPE, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["admin_id"],
            ["admins.id"],
            name=op.f("fk_final_leaderboards_admin_id_admins"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_final_leaderboards")),
    )
    #  store price change history 
    op.create_table(
        "price_changes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=32), nullable=False),
        sa.Column("old_value", sa.Integer(), nullable=False),
        sa.Column("new_value", sa.Integer(), nullable=False),
        sa.Column("admin_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["admin_id"],
            ["admins.id"],
            name=op.f("fk_price_changes_admin_id_admins"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_price_changes")),
    )
    # Team logins and and updates
    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("session_version", sa.Integer(), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("powerups_used", sa.Integer(), nullable=False),
        sa.Column("playthroughs", sa.Integer(), nullable=False),
        sa.Column("has_reached_delhi", sa.Boolean(), nullable=False),
        sa.Column("reached_delhi_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_path_id", sa.Integer(), nullable=True),
        sa.Column("switch_from_path_id", sa.Integer(), nullable=True),
        sa.Column("frozen_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("points >= 0", name=op.f("ck_teams_points_non_negative")),
        sa.ForeignKeyConstraint(
            ["current_path_id"],
            ["paths.id"],
            name=op.f("fk_teams_current_path_id_paths"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["switch_from_path_id"],
            ["paths.id"],
            name=op.f("fk_teams_switch_from_path_id_paths"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_teams")),
        sa.UniqueConstraint("username", name=op.f("uq_teams_username")),
    )
    # Monument challenges.
    op.create_table(
        "questions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("story", sa.Text(), nullable=False),
        sa.Column("monument", sa.String(length=128), nullable=False),
        sa.Column("hint1", sa.Text(), nullable=True),
        sa.Column("hint2", sa.Text(), nullable=True),
        sa.Column("file_path", sa.String(length=255), nullable=True),
        sa.Column("flag", sa.String(length=256), nullable=False),
        sa.Column("case_sensitive", sa.Boolean(), nullable=False),
        sa.Column("is_final", sa.Boolean(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("base_points", sa.Integer(), nullable=False),
        sa.Column("min_points", sa.Integer(), nullable=False),
        sa.Column("decay_interval_seconds", sa.Integer(), nullable=False),
        sa.Column("decay_points", sa.Integer(), nullable=False),
        sa.Column("retries", sa.Integer(), nullable=False),
        sa.Column("block_seconds", sa.Integer(), nullable=False),
        sa.Column("unlocked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("unlocked_game_seconds", sa.Integer(), nullable=True),
        sa.Column("unlocked_by_team_id", sa.Integer(), nullable=True),
        sa.Column("first_solved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_solved_by_team_id", sa.Integer(), nullable=True),
        sa.Column("blocked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("blocked_by_team_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["blocked_by_team_id"],
            ["teams.id"],
            name=op.f("fk_questions_blocked_by_team_id_teams"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["first_solved_by_team_id"],
            ["teams.id"],
            name=op.f("fk_questions_first_solved_by_team_id_teams"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["unlocked_by_team_id"],
            ["teams.id"],
            name=op.f("fk_questions_unlocked_by_team_id_teams"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_questions")),
        sa.UniqueConstraint("code", name=op.f("uq_questions_code")),
    )
    # Question order on each path.
    op.create_table(
        "path_questions",
        sa.Column("path_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["path_id"],
            ["paths.id"],
            name=op.f("fk_path_questions_path_id_paths"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["questions.id"],
            name=op.f("fk_path_questions_question_id_questions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("path_id", "position", name=op.f("pk_path_questions")),
        sa.UniqueConstraint("path_id", "question_id", name=op.f("uq_path_questions_path_id")),
    )
    # Every point change.
    op.create_table(
        "point_ledger",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("delta", sa.Integer(), nullable=False),
        sa.Column("balance_after", sa.Integer(), nullable=False),
        sa.Column(
            "reason",
            sa.Enum(
                "solve",
                "hint",
                "retry",
                "skip",
                "path_switch",
                "admin_adjust",
                name="ledgerreason",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("question_id", sa.Uuid(), nullable=True),
        sa.Column("admin_id", sa.Integer(), nullable=True),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["admin_id"],
            ["admins.id"],
            name=op.f("fk_point_ledger_admin_id_admins"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["questions.id"],
            name=op.f("fk_point_ledger_question_id_questions"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["team_id"],
            ["teams.id"],
            name=op.f("fk_point_ledger_team_id_teams"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_point_ledger")),
    )
    op.create_index(op.f("ix_point_ledger_team_id"), "point_ledger", ["team_id"])
    # Team question events  logs
    op.create_table(
        "team_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=True),
        sa.Column(
            "event",
            sa.Enum(
                "view",
                "answer_correct",
                "answer_wrong",
                "retry_purchased",
                "skipped",
                "wait_apply",
                "cancelled_timer",
                "leave",
                "h1_purchased",
                "h2_purchased",
                "h12_purchased",
                "blocked",
                name="questionevent",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("meta", JSON_TYPE, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["questions.id"],
            name=op.f("fk_team_logs_question_id_questions"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["team_id"], ["teams.id"], name=op.f("fk_team_logs_team_id_teams"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_team_logs")),
    )
    op.create_index("ix_team_logs_team_created", "team_logs", ["team_id", "created_at"])
    # Team route events maps
    op.create_table(
        "team_path_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("path_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=True),
        sa.Column(
            "event",
            sa.Enum(
                "start",
                "cleared",
                "left",
                "wait",
                "end",
                "cancelled",
                name="pathevent",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["path_id"],
            ["paths.id"],
            name=op.f("fk_team_path_events_path_id_paths"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["questions.id"],
            name=op.f("fk_team_path_events_question_id_questions"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["team_id"],
            ["teams.id"],
            name=op.f("fk_team_path_events_team_id_teams"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_team_path_events")),
    )
    op.create_index(op.f("ix_team_path_events_team_id"), "team_path_events", ["team_id"])
    # Per-team progress on ques
    op.create_table(
        "team_question_states",
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "active", "solved", "skipped", name="questionstatus", native_enum=False, length=32
            ),
            nullable=False,
        ),
        sa.Column("attempts_used", sa.Integer(), nullable=False),
        sa.Column("extra_retries", sa.Integer(), nullable=False),
        sa.Column("hint1_owned", sa.Boolean(), nullable=False),
        sa.Column("hint2_owned", sa.Boolean(), nullable=False),
        sa.Column("points_awarded", sa.Integer(), nullable=False),
        sa.Column("viewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("wait_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("solved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["questions.id"],
            name=op.f("fk_team_question_states_question_id_questions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["team_id"],
            ["teams.id"],
            name=op.f("fk_team_question_states_team_id_teams"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("team_id", "question_id", name=op.f("pk_team_question_states")),
    )


def downgrade() -> None:
    op.drop_table("team_question_states")
    op.drop_index(op.f("ix_team_path_events_team_id"), table_name="team_path_events")
    op.drop_table("team_path_events")
    op.drop_index("ix_team_logs_team_created", table_name="team_logs")
    op.drop_table("team_logs")
    op.drop_index(op.f("ix_point_ledger_team_id"), table_name="point_ledger")
    op.drop_table("point_ledger")
    op.drop_table("path_questions")
    op.drop_table("questions")
    op.drop_table("teams")
    op.drop_table("price_changes")
    op.drop_table("final_leaderboards")
    op.drop_table("admin_audit")
    op.drop_table("store_prices")
    op.drop_table("paths")
    op.drop_table("game_state")
    op.drop_table("admins")

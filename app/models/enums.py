from enum import StrEnum

from sqlalchemy import Enum


class GameStatus(StrEnum):
    NOT_STARTED = "not_started"
    RUNNING = "running"
    PAUSED = "paused"
    ENDED = "ended"


class QuestionStatus(StrEnum):
    ACTIVE = "active"
    SOLVED = "solved"
    SKIPPED = "skipped"


class LedgerReason(StrEnum):
    SOLVE = "solve"
    HINT = "hint"
    RETRY = "retry"
    SKIP = "skip"
    PATH_SWITCH = "path_switch"
    ADMIN_ADJUST = "admin_adjust"


class QuestionEvent(StrEnum):
    VIEW = "view"
    ANSWER_CORRECT = "answer_correct"
    ANSWER_WRONG = "answer_wrong"
    RETRY_PURCHASED = "retry_purchased"
    SKIPPED = "skipped"
    WAIT_APPLY = "wait_apply"
    CANCELLED_TIMER = "cancelled_timer"
    LEAVE = "leave"
    H1_PURCHASED = "h1_purchased"
    H2_PURCHASED = "h2_purchased"
    H12_PURCHASED = "h12_purchased"
    BLOCKED = "blocked"


class PathEvent(StrEnum):
    START = "start"
    CLEARED = "cleared"
    LEFT = "left"
    WAIT = "wait"
    END = "end"
    CANCELLED = "cancelled"


def str_enum(enum_cls: type[StrEnum]) -> Enum:
    return Enum(
        enum_cls,
        native_enum=False,
        length=32,
        values_callable=lambda members: [m.value for m in members],
        validate_strings=True,
    )

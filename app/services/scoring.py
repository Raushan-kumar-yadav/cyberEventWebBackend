from app.models import Question


# step decay from first unlock 
def current_points(question: Question, active_now: int) -> int:
    if question.unlocked_game_seconds is None or question.decay_interval_seconds <= 0:
        return question.base_points
    elapsed = max(0, active_now - question.unlocked_game_seconds)
    steps = elapsed // question.decay_interval_seconds
    return max(question.min_points, question.base_points - steps * question.decay_points)


def next_drop_in(question: Question, active_now: int) -> int | None:
    if (
        question.unlocked_game_seconds is None
        or question.decay_interval_seconds <= 0
        or question.decay_points <= 0
        or current_points(question, active_now) <= question.min_points
    ):
        return None
    elapsed = max(0, active_now - question.unlocked_game_seconds)
    return question.decay_interval_seconds - elapsed % question.decay_interval_seconds

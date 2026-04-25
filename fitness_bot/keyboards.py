from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from .models import Exercise


class WorkoutCallback(CallbackData, prefix="wk"):
    action: str  # "add_exercise" | "publish"
    workout_id: int


class ExerciseCallback(CallbackData, prefix="ex"):
    action: str  # "log" | "skip_comment"
    exercise_id: int
    session_id: int


class WorkoutCompleteCallback(CallbackData, prefix="wc"):
    session_id: int


def after_sets_kb(workout_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="➕ Add another exercise",
        callback_data=WorkoutCallback(action="add_exercise", workout_id=workout_id),
    )
    builder.button(
        text="✅ Publish workout",
        callback_data=WorkoutCallback(action="publish", workout_id=workout_id),
    )
    builder.adjust(1)
    return builder.as_markup()


def exercise_list_kb(
    exercises: list[Exercise],
    done_exercise_ids: set[int],
    session_id: int,
    all_done: bool,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for ex in exercises:
        done = ex.id in done_exercise_ids
        label = f"{'✅' if done else '⬜'} {ex.description[:35]}"
        builder.button(
            text=label,
            callback_data=ExerciseCallback(action="log", exercise_id=ex.id, session_id=session_id),
        )
    if all_done:
        builder.button(
            text="🏁 Complete Workout",
            callback_data=WorkoutCompleteCallback(session_id=session_id),
        )
    builder.adjust(1)
    return builder.as_markup()


def skip_comment_kb(exercise_id: int, session_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="Skip comment",
        callback_data=ExerciseCallback(
            action="skip_comment", exercise_id=exercise_id, session_id=session_id
        ),
    )
    return builder.as_markup()

from datetime import datetime, timezone

from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from ..db import async_session
from ..filters import RoleFilter
from ..keyboards import (
    ExerciseCallback,
    WorkoutCompleteCallback,
    exercise_list_kb,
    skip_comment_kb,
)
from ..models import (
    Exercise,
    ExecutedSet,
    ExerciseComment,
    PlannedSet,
    User,
    Workout,
    WorkoutSession,
)
from ..states import TraineeStates

router = Router()
router.message.filter(RoleFilter("trainee"))
router.callback_query.filter(RoleFilter("trainee"))


async def _get_or_create_session(workout_id: int, trainee_id: int) -> WorkoutSession:
    async with async_session() as db:
        result = await db.execute(
            select(WorkoutSession)
            .where(WorkoutSession.workout_id == workout_id)
            .where(WorkoutSession.trainee_telegram_id == trainee_id)
            .where(WorkoutSession.completed_at.is_(None))
        )
        session_obj = result.scalar_one_or_none()
        if not session_obj:
            session_obj = WorkoutSession(
                workout_id=workout_id, trainee_telegram_id=trainee_id
            )
            db.add(session_obj)
            await db.commit()
            await db.refresh(session_obj)
        return session_obj


async def _send_workout_view(chat_id: int, trainee_id: int, bot: Bot) -> None:
    async with async_session() as db:
        result = await db.execute(
            select(Workout)
            .where(Workout.is_published == True)
            .options(
                selectinload(Workout.exercises).selectinload(Exercise.planned_sets)
            )
            .order_by(Workout.created_at.desc())
            .limit(1)
        )
        workout = result.scalar_one_or_none()

    if not workout:
        await bot.send_message(chat_id, "No workout available yet.")
        return

    session_obj = await _get_or_create_session(workout.id, trainee_id)

    async with async_session() as db:
        exec_result = await db.execute(
            select(ExecutedSet).where(ExecutedSet.session_id == session_obj.id)
        )
        executed_planned_ids = {es.planned_set_id for es in exec_result.scalars().all()}

    done_exercise_ids: set[int] = set()
    for exercise in workout.exercises:
        if exercise.planned_sets and all(
            ps.id in executed_planned_ids for ps in exercise.planned_sets
        ):
            done_exercise_ids.add(exercise.id)

    all_done = len(done_exercise_ids) == len(workout.exercises)

    lines = [f"Your workout ({len(workout.exercises)} exercises):\n"]
    for i, ex in enumerate(workout.exercises, 1):
        icon = "✅" if ex.id in done_exercise_ids else "⬜"
        lines.append(f"{icon} {i}. {ex.description}")

    await bot.send_message(
        chat_id,
        "\n".join(lines),
        reply_markup=exercise_list_kb(
            workout.exercises, done_exercise_ids, session_obj.id, all_done
        ),
    )


@router.message(Command("workout"))
async def cmd_workout(message: Message, bot: Bot) -> None:
    await _send_workout_view(message.chat.id, message.from_user.id, bot)


@router.callback_query(ExerciseCallback.filter())
async def cb_log_exercise(
    callback: CallbackQuery, callback_data: ExerciseCallback, state: FSMContext
) -> None:
    if callback_data.action != "log":
        await callback.answer()
        return

    exercise_id = callback_data.exercise_id
    session_id = callback_data.session_id

    async with async_session() as db:
        exercise = await db.get(
            Exercise, exercise_id, options=[selectinload(Exercise.planned_sets)]
        )
        if not exercise or not exercise.planned_sets:
            await callback.answer("Exercise not found or has no sets.")
            return

        planned_set_ids = [ps.id for ps in exercise.planned_sets]
        await db.execute(
            delete(ExecutedSet).where(
                ExecutedSet.session_id == session_id,
                ExecutedSet.planned_set_id.in_(planned_set_ids),
            )
        )
        await db.execute(
            delete(ExerciseComment).where(
                ExerciseComment.session_id == session_id,
                ExerciseComment.exercise_id == exercise_id,
            )
        )
        await db.commit()

    await state.set_state(TraineeStates.logging_set_reps)
    await state.update_data(
        session_id=session_id,
        exercise_id=exercise_id,
        planned_set_ids=planned_set_ids,
        current_set_index=0,
    )
    await _prompt_set_reps(callback.message, exercise, exercise.planned_sets, 0)
    await callback.answer()


async def _prompt_set_reps(
    message: Message,
    exercise: Exercise,
    planned_sets: list[PlannedSet],
    index: int,
) -> None:
    ps = planned_sets[index]
    planned = _fmt_planned(ps)
    await message.answer(
        f"{exercise.description}\n"
        f"Set {ps.set_number} of {len(planned_sets)}{planned}\n\n"
        "Enter actual reps (or 'skip'):"
    )


def _fmt_planned(ps: PlannedSet) -> str:
    parts = []
    if ps.reps is not None:
        parts.append(f"{ps.reps} reps")
    if ps.weight is not None:
        parts.append(f"{ps.weight}kg")
    if not parts:
        return ""
    return f" — planned: {' @ '.join(parts)}"


@router.message(TraineeStates.logging_set_reps)
async def handle_log_reps(message: Message, state: FSMContext) -> None:
    text = message.text.strip().lower()
    reps = None
    if text != "skip":
        try:
            reps = int(text)
        except ValueError:
            await message.answer("Enter a number or 'skip'.")
            return

    await state.update_data(current_reps=reps)
    await state.set_state(TraineeStates.logging_set_weight)
    await message.answer("Weight in kg (or 'skip'):")


@router.message(TraineeStates.logging_set_weight)
async def handle_log_weight(message: Message, state: FSMContext, bot: Bot) -> None:
    text = message.text.strip().lower().replace("kg", "").strip()
    weight = None
    if text != "skip":
        try:
            weight = float(text.replace(",", "."))
        except ValueError:
            await message.answer("Enter a number or 'skip'.")
            return

    data = await state.get_data()
    session_id: int = data["session_id"]
    exercise_id: int = data["exercise_id"]
    planned_set_ids: list[int] = data["planned_set_ids"]
    current_index: int = data["current_set_index"]
    current_reps: int | None = data["current_reps"]

    async with async_session() as db:
        db.add(
            ExecutedSet(
                session_id=session_id,
                planned_set_id=planned_set_ids[current_index],
                actual_reps=current_reps,
                actual_weight=weight,
            )
        )
        await db.commit()

    next_index = current_index + 1
    if next_index < len(planned_set_ids):
        await state.update_data(current_set_index=next_index)
        await state.set_state(TraineeStates.logging_set_reps)

        async with async_session() as db:
            exercise = await db.get(
                Exercise, exercise_id, options=[selectinload(Exercise.planned_sets)]
            )
        await _prompt_set_reps(message, exercise, exercise.planned_sets, next_index)
    else:
        await state.set_state(TraineeStates.adding_comment)
        await message.answer(
            "All sets logged! Add a comment for this exercise (or tap Skip):",
            reply_markup=skip_comment_kb(exercise_id, session_id),
        )


@router.message(TraineeStates.adding_comment)
async def handle_comment(message: Message, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    async with async_session() as db:
        db.add(
            ExerciseComment(
                session_id=data["session_id"],
                exercise_id=data["exercise_id"],
                comment=message.text.strip(),
            )
        )
        await db.commit()

    await state.clear()
    await message.answer("Comment saved!")
    await _send_workout_view(message.chat.id, message.from_user.id, bot)


@router.callback_query(ExerciseCallback.filter())
async def cb_skip_comment(
    callback: CallbackQuery, callback_data: ExerciseCallback, state: FSMContext, bot: Bot
) -> None:
    if callback_data.action != "skip_comment":
        await callback.answer()
        return
    await state.clear()
    await callback.message.answer("No comment added.")
    await _send_workout_view(callback.message.chat.id, callback.from_user.id, bot)
    await callback.answer()


@router.callback_query(WorkoutCompleteCallback.filter())
async def cb_complete_workout(
    callback: CallbackQuery, callback_data: WorkoutCompleteCallback, bot: Bot
) -> None:
    async with async_session() as db:
        session_obj = await db.get(WorkoutSession, callback_data.session_id)
        if not session_obj or session_obj.completed_at:
            await callback.answer("Session not found or already completed.")
            return
        session_obj.completed_at = datetime.now(timezone.utc)
        await db.commit()

        trainers = (await db.execute(select(User).where(User.role == "trainer"))).scalars().all()

    await callback.message.answer("Workout completed! Great job!")
    for trainer in trainers:
        await bot.send_message(trainer.telegram_id, "Your trainee completed their workout! Use /report to see results.")
    await callback.answer()

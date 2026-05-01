from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..db import async_session
from ..filters import RoleFilter
from ..keyboards import WorkoutCallback, after_sets_kb
from ..models import Exercise, ExecutedSet, PlannedSet, User, Workout, WorkoutSession
from ..reports import format_report
from ..states import TrainerStates

router = Router()
router.message.filter(RoleFilter("trainer"))
router.callback_query.filter(RoleFilter("trainer"))


@router.message(Command("new_workout"))
async def cmd_new_workout(message: Message, state: FSMContext) -> None:
    await state.clear()
    async with async_session() as db:
        workout = Workout()
        db.add(workout)
        await db.commit()
        await db.refresh(workout)

    await state.set_state(TrainerStates.adding_exercise_description)
    await state.update_data(workout_id=workout.id, exercise_order=1)
    await message.answer("New workout created.\n\nExercise 1 — enter description:")


@router.message(TrainerStates.adding_exercise_description)
async def handle_exercise_description(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    async with async_session() as db:
        exercise = Exercise(
            workout_id=data["workout_id"],
            description=message.text.strip(),
            order=data["exercise_order"],
        )
        db.add(exercise)
        await db.commit()
        await db.refresh(exercise)

    await state.update_data(exercise_id=exercise.id)
    await state.set_state(TrainerStates.adding_exercise_set_count)
    await message.answer("How many sets?")


@router.message(TrainerStates.adding_exercise_set_count)
async def handle_set_count(message: Message, state: FSMContext) -> None:
    try:
        count = int(message.text.strip())
        if count < 1:
            raise ValueError
    except ValueError:
        await message.answer("Please enter a positive number.")
        return

    await state.update_data(set_count=count, current_set=1)
    await state.set_state(TrainerStates.adding_set_reps)
    await message.answer(f"Set 1 of {count} — enter reps (or 'skip'):")


@router.message(TrainerStates.adding_set_reps)
async def handle_set_reps(message: Message, state: FSMContext) -> None:
    text = message.text.strip().lower()
    reps = None
    if text != "skip":
        try:
            reps = int(text)
        except ValueError:
            await message.answer("Enter a number or 'skip'.")
            return

    await state.update_data(current_reps=reps)
    await state.set_state(TrainerStates.adding_set_weight)
    await message.answer("Weight in kg (or 'skip'):")


@router.message(TrainerStates.adding_set_weight)
async def handle_set_weight(message: Message, state: FSMContext) -> None:
    text = message.text.strip().lower().replace("kg", "").strip()
    weight = None
    if text != "skip":
        try:
            weight = float(text.replace(",", "."))
        except ValueError:
            await message.answer("Enter a number or 'skip'.")
            return

    data = await state.get_data()
    async with async_session() as db:
        planned_set = PlannedSet(
            exercise_id=data["exercise_id"],
            set_number=data["current_set"],
            reps=data["current_reps"],
            weight=weight,
        )
        db.add(planned_set)
        await db.commit()

    current_set = data["current_set"]
    set_count = data["set_count"]

    if current_set < set_count:
        await state.update_data(current_set=current_set + 1)
        await state.set_state(TrainerStates.adding_set_reps)
        await message.answer(f"Set {current_set + 1} of {set_count} — enter reps (or 'skip'):")
    else:
        next_order = data["exercise_order"] + 1
        await state.update_data(exercise_order=next_order)
        await state.set_state(TrainerStates.adding_exercise_description)
        await message.answer(
            "Exercise saved! What next?",
            reply_markup=after_sets_kb(data["workout_id"]),
        )


@router.callback_query(WorkoutCallback.filter())
async def cb_add_exercise(
    callback: CallbackQuery, callback_data: WorkoutCallback, state: FSMContext
) -> None:
    if callback_data.action == "add_exercise":
        data = await state.get_data()
        order = data.get("exercise_order", 1)
        await state.set_state(TrainerStates.adding_exercise_description)
        await callback.message.answer(f"Exercise {order} — enter description:")
        await callback.answer()


@router.callback_query(WorkoutCallback.filter())
async def cb_publish_workout(
    callback: CallbackQuery, callback_data: WorkoutCallback, state: FSMContext, bot: Bot
) -> None:
    if callback_data.action != "publish":
        await callback.answer()
        return

    async with async_session() as db:
        workout = await db.get(
            Workout,
            callback_data.workout_id,
            options=[selectinload(Workout.exercises)],
        )
        if not workout:
            await callback.answer("Workout not found.")
            return
        if workout.is_published:
            await callback.answer("Already published.")
            return
        if not workout.exercises:
            await callback.answer("Add at least one exercise before publishing.")
            return
        workout.is_published = True
        await db.commit()

        trainees = (await db.execute(select(User).where(User.role == "trainee"))).scalars().all()

    await state.clear()
    await callback.message.answer("Workout published!")
    for trainee in trainees:
        await bot.send_message(trainee.telegram_id, "New workout is ready! Use /workout to see it.")
    await callback.answer()


@router.message(Command("report"))
async def cmd_report(message: Message) -> None:
    async with async_session() as db:
        result = await db.execute(
            select(WorkoutSession)
            .where(WorkoutSession.completed_at.is_not(None))
            .order_by(WorkoutSession.completed_at.desc())
            .options(
                selectinload(WorkoutSession.workout)
                    .selectinload(Workout.exercises)
                    .selectinload(Exercise.planned_sets),
                selectinload(WorkoutSession.executed_sets)
                    .selectinload(ExecutedSet.planned_set),
                selectinload(WorkoutSession.comments),
            )
            .limit(1)
        )
        session_obj = result.scalar_one_or_none()

    if not session_obj:
        await message.answer("No completed workouts yet.")
        return

    await message.answer(format_report(session_obj))

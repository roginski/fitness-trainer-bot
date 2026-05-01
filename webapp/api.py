from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from fitness_bot.config import BOT_TOKEN, TRAINER_ID, TRAINEE_ID
from fitness_bot.db import async_session
from fitness_bot.models import (
    Exercise,
    ExecutedSet,
    ExerciseComment,
    PlannedSet,
    Workout,
    WorkoutSession,
)
from webapp.auth import get_current_user

router = APIRouter(prefix="/api")


async def _send_telegram(chat_id: int, text: str) -> None:
    async with httpx.AsyncClient() as client:
        await client.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text},
        )


def _serialize_exercises(exercises: list[Exercise]) -> list[dict]:
    return [
        {
            "id": ex.id,
            "description": ex.description,
            "order": ex.order,
            "planned_sets": [
                {"id": ps.id, "set_number": ps.set_number, "reps": ps.reps, "weight": ps.weight}
                for ps in ex.planned_sets
            ],
        }
        for ex in exercises
    ]


# ---------------------------------------------------------------------------
# Trainer endpoints
# ---------------------------------------------------------------------------

@router.get("/workout/draft")
async def get_or_create_draft(current_user: int = Depends(get_current_user)):
    if current_user != TRAINER_ID:
        raise HTTPException(403)

    async with async_session() as db:
        result = await db.execute(
            select(Workout)
            .where(Workout.is_published == False)
            .options(selectinload(Workout.exercises).selectinload(Exercise.planned_sets))
            .order_by(Workout.created_at.desc())
            .limit(1)
        )
        workout = result.scalar_one_or_none()

        if not workout:
            workout = Workout()
            db.add(workout)
            await db.commit()
            return {"workout_id": workout.id, "exercises": []}

        return {"workout_id": workout.id, "exercises": _serialize_exercises(workout.exercises)}


class SetIn(BaseModel):
    reps: int | None = None
    weight: float | None = None


class ExerciseIn(BaseModel):
    description: str
    sets: list[SetIn]


@router.post("/workout/{workout_id}/exercises")
async def add_exercise(workout_id: int, body: ExerciseIn, current_user: int = Depends(get_current_user)):
    if current_user != TRAINER_ID:
        raise HTTPException(403)

    async with async_session() as db:
        result = await db.execute(
            select(Exercise)
            .where(Exercise.workout_id == workout_id)
            .order_by(Exercise.order.desc())
            .limit(1)
        )
        last = result.scalar_one_or_none()
        order = (last.order + 1) if last else 1

        exercise = Exercise(workout_id=workout_id, description=body.description, order=order)
        db.add(exercise)
        await db.flush()

        for i, s in enumerate(body.sets, 1):
            db.add(PlannedSet(exercise_id=exercise.id, set_number=i, reps=s.reps, weight=s.weight))

        await db.commit()

        result = await db.execute(
            select(Exercise)
            .where(Exercise.workout_id == workout_id)
            .options(selectinload(Exercise.planned_sets))
            .order_by(Exercise.order)
        )
        exercises = result.scalars().all()
        return {"exercises": _serialize_exercises(exercises)}


@router.delete("/exercises/{exercise_id}")
async def remove_exercise(exercise_id: int, current_user: int = Depends(get_current_user)):
    if current_user != TRAINER_ID:
        raise HTTPException(403)

    async with async_session() as db:
        exercise = await db.get(Exercise, exercise_id)
        if not exercise:
            raise HTTPException(404)
        workout_id = exercise.workout_id
        await db.delete(exercise)
        await db.commit()

        result = await db.execute(
            select(Exercise)
            .where(Exercise.workout_id == workout_id)
            .options(selectinload(Exercise.planned_sets))
            .order_by(Exercise.order)
        )
        return {"exercises": _serialize_exercises(result.scalars().all())}


@router.post("/workout/{workout_id}/publish")
async def publish_workout(workout_id: int, current_user: int = Depends(get_current_user)):
    if current_user != TRAINER_ID:
        raise HTTPException(403)

    async with async_session() as db:
        workout = await db.get(Workout, workout_id)
        if not workout:
            raise HTTPException(404)
        workout.is_published = True
        await db.commit()

    await _send_telegram(TRAINEE_ID, "New workout is ready! Open the app to start.")
    return {"status": "published"}


# ---------------------------------------------------------------------------
# Trainee endpoints
# ---------------------------------------------------------------------------

@router.get("/workout/current")
async def get_current_workout(current_user: int = Depends(get_current_user)):
    if current_user != TRAINEE_ID:
        raise HTTPException(403)

    async with async_session() as db:
        result = await db.execute(
            select(Workout)
            .where(Workout.is_published == True)
            .options(selectinload(Workout.exercises).selectinload(Exercise.planned_sets))
            .order_by(Workout.created_at.desc())
            .limit(1)
        )
        workout = result.scalar_one_or_none()
        if not workout:
            return {"workout": None}

        sess_result = await db.execute(
            select(WorkoutSession)
            .where(WorkoutSession.workout_id == workout.id)
            .where(WorkoutSession.trainee_telegram_id == current_user)
            .where(WorkoutSession.completed_at.is_(None))
        )
        session = sess_result.scalar_one_or_none()
        if not session:
            session = WorkoutSession(workout_id=workout.id, trainee_telegram_id=current_user)
            db.add(session)
            await db.commit()
            await db.refresh(session)

        exec_result = await db.execute(
            select(ExecutedSet).where(ExecutedSet.session_id == session.id)
        )
        executed = {
            es.planned_set_id: {"reps": es.actual_reps, "weight": es.actual_weight}
            for es in exec_result.scalars().all()
        }

        comment_result = await db.execute(
            select(ExerciseComment).where(ExerciseComment.session_id == session.id)
        )
        comments = {c.exercise_id: c.comment for c in comment_result.scalars().all()}

        return {
            "session_id": session.id,
            "workout": {
                "id": workout.id,
                "exercises": [
                    {
                        "id": ex.id,
                        "description": ex.description,
                        "comment": comments.get(ex.id),
                        "planned_sets": [
                            {
                                "id": ps.id,
                                "set_number": ps.set_number,
                                "reps": ps.reps,
                                "weight": ps.weight,
                                "executed": executed.get(ps.id),
                            }
                            for ps in ex.planned_sets
                        ],
                    }
                    for ex in workout.exercises
                ],
            },
        }


class LogSetIn(BaseModel):
    session_id: int
    planned_set_id: int
    actual_reps: int | None = None
    actual_weight: float | None = None


@router.post("/sets/log")
async def log_set(body: LogSetIn, current_user: int = Depends(get_current_user)):
    if current_user != TRAINEE_ID:
        raise HTTPException(403)

    async with async_session() as db:
        await db.execute(
            delete(ExecutedSet).where(
                ExecutedSet.session_id == body.session_id,
                ExecutedSet.planned_set_id == body.planned_set_id,
            )
        )
        db.add(ExecutedSet(
            session_id=body.session_id,
            planned_set_id=body.planned_set_id,
            actual_reps=body.actual_reps,
            actual_weight=body.actual_weight,
        ))
        await db.commit()
    return {"status": "ok"}


class CommentIn(BaseModel):
    session_id: int
    exercise_id: int
    comment: str


@router.post("/comments")
async def save_comment(body: CommentIn, current_user: int = Depends(get_current_user)):
    if current_user != TRAINEE_ID:
        raise HTTPException(403)

    async with async_session() as db:
        await db.execute(
            delete(ExerciseComment).where(
                ExerciseComment.session_id == body.session_id,
                ExerciseComment.exercise_id == body.exercise_id,
            )
        )
        db.add(ExerciseComment(
            session_id=body.session_id,
            exercise_id=body.exercise_id,
            comment=body.comment,
        ))
        await db.commit()
    return {"status": "ok"}


@router.post("/sessions/{session_id}/complete")
async def complete_session(session_id: int, current_user: int = Depends(get_current_user)):
    if current_user != TRAINEE_ID:
        raise HTTPException(403)

    async with async_session() as db:
        session = await db.get(WorkoutSession, session_id)
        if not session:
            raise HTTPException(404)
        session.completed_at = datetime.now(timezone.utc)
        await db.commit()

    await _send_telegram(TRAINER_ID, "Your trainee completed their workout! Use /report to see results.")
    return {"status": "ok"}

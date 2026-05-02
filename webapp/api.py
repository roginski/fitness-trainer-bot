from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from fitness_bot.config import BOT_TOKEN
from fitness_bot.db import async_session
from fitness_bot.models import (
    Exercise,
    ExecutedSet,
    ExerciseComment,
    PlannedSet,
    User,
    Workout,
    WorkoutSession,
)
from webapp.auth import get_current_user
from webapp.limiter import limiter

router = APIRouter(prefix="/api")


def _utc_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


async def _send_telegram(chat_id: int, text: str) -> None:
    async with httpx.AsyncClient() as client:
        await client.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text},
        )


async def _notify_all(role: str, text: str) -> None:
    async with async_session() as db:
        result = await db.execute(select(User).where(User.role == role))
        users = result.scalars().all()
    for user in users:
        await _send_telegram(user.telegram_id, text)


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


async def require_trainer(current_user: int = Depends(get_current_user)) -> int:
    async with async_session() as db:
        user = await db.get(User, current_user)
    if not user or user.role != "trainer":
        raise HTTPException(403)
    return current_user


async def require_trainee(current_user: int = Depends(get_current_user)) -> int:
    async with async_session() as db:
        user = await db.get(User, current_user)
    if not user or user.role != "trainee":
        raise HTTPException(403)
    return current_user


# ---------------------------------------------------------------------------
# Trainer endpoints
# ---------------------------------------------------------------------------

@router.get("/workout/draft")
@limiter.limit("60/minute")
async def get_or_create_draft(request: Request, current_user: int = Depends(require_trainer)):
    async with async_session() as db:
        result = await db.execute(
            select(Workout)
            .where(Workout.is_published == False)
            .options(selectinload(Workout.exercises).selectinload(Exercise.planned_sets))
            .order_by(Workout.created_at.desc())
            .limit(1)
        )
        workout = result.scalar_one_or_none()

        if workout:
            return {"workout_id": workout.id, "is_published": False, "exercises": _serialize_exercises(workout.exercises)}

        # No draft — fall back to latest published workout
        result = await db.execute(
            select(Workout)
            .where(Workout.is_published == True)
            .options(selectinload(Workout.exercises).selectinload(Exercise.planned_sets))
            .order_by(Workout.created_at.desc())
            .limit(1)
        )
        workout = result.scalar_one_or_none()

        if workout:
            return {"workout_id": workout.id, "is_published": True, "exercises": _serialize_exercises(workout.exercises)}

        # Nothing exists — create a fresh draft
        workout = Workout()
        db.add(workout)
        await db.commit()
        return {"workout_id": workout.id, "is_published": False, "exercises": []}


class SetIn(BaseModel):
    reps: int | None = Field(default=None, ge=0, le=9999)
    weight: float | None = Field(default=None, ge=0, le=9999)


class ExerciseIn(BaseModel):
    description: str = Field(min_length=1, max_length=200)
    sets: list[SetIn] = Field(min_length=1, max_length=20)


@router.post("/workout/{workout_id}/exercises")
@limiter.limit("30/minute")
async def add_exercise(request: Request, workout_id: int, body: ExerciseIn, current_user: int = Depends(require_trainer)):
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


class SetUpdateIn(BaseModel):
    reps: int | None = Field(default=None, ge=0, le=9999)
    weight: float | None = Field(default=None, ge=0, le=9999)


@router.patch("/sets/{planned_set_id}")
@limiter.limit("60/minute")
async def update_planned_set(request: Request, planned_set_id: int, body: SetUpdateIn, current_user: int = Depends(require_trainer)):
    async with async_session() as db:
        ps = await db.get(PlannedSet, planned_set_id)
        if not ps:
            raise HTTPException(404)
        if "reps" in body.model_fields_set:
            ps.reps = body.reps
        if "weight" in body.model_fields_set:
            ps.weight = body.weight
        await db.commit()
    return {"status": "ok"}


class ReorderIn(BaseModel):
    exercise_ids: list[int]


@router.post("/workout/{workout_id}/exercises/reorder")
@limiter.limit("30/minute")
async def reorder_exercises(request: Request, workout_id: int, body: ReorderIn, current_user: int = Depends(require_trainer)):
    async with async_session() as db:
        for new_order, ex_id in enumerate(body.exercise_ids, 1):
            exercise = await db.get(Exercise, ex_id)
            if exercise and exercise.workout_id == workout_id:
                exercise.order = new_order
        await db.commit()
    return {"status": "ok"}


@router.delete("/exercises/{exercise_id}")
@limiter.limit("30/minute")
async def remove_exercise(request: Request, exercise_id: int, current_user: int = Depends(require_trainer)):
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
@limiter.limit("10/minute")
async def publish_workout(request: Request, workout_id: int, current_user: int = Depends(require_trainer)):
    async with async_session() as db:
        workout = await db.get(Workout, workout_id)
        if not workout:
            raise HTTPException(404)
        workout.is_published = True
        await db.commit()

    await _notify_all("trainee", "New workout is ready! Open the app to start.")
    return {"status": "published"}


@router.post("/workout/new")
@limiter.limit("10/minute")
async def create_new_draft(request: Request, current_user: int = Depends(require_trainer)):
    async with async_session() as db:
        workout = Workout()
        db.add(workout)
        await db.commit()
    return {"workout_id": workout.id, "is_published": False, "exercises": []}


@router.post("/workout/{workout_id}/notify")
@limiter.limit("10/minute")
async def notify_workout_update(request: Request, workout_id: int, current_user: int = Depends(require_trainer)):
    async with async_session() as db:
        workout = await db.get(Workout, workout_id)
        if not workout or not workout.is_published:
            raise HTTPException(404)
    await _notify_all("trainee", "Your workout has been updated! Open the app to see changes.")
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Trainee endpoints
# ---------------------------------------------------------------------------

@router.get("/workout/current")
@limiter.limit("60/minute")
async def get_current_workout(request: Request, current_user: int = Depends(require_trainee)):
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
    actual_reps: int | None = Field(default=None, ge=0, le=9999)
    actual_weight: float | None = Field(default=None, ge=0, le=9999)


@router.post("/sets/log")
@limiter.limit("60/minute")
async def log_set(request: Request, body: LogSetIn, current_user: int = Depends(require_trainee)):
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
    comment: str = Field(min_length=1, max_length=1000)


@router.post("/comments")
@limiter.limit("30/minute")
async def save_comment(request: Request, body: CommentIn, current_user: int = Depends(require_trainee)):
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
@limiter.limit("10/minute")
async def complete_session(request: Request, session_id: int, current_user: int = Depends(require_trainee)):
    async with async_session() as db:
        session = await db.get(WorkoutSession, session_id)
        if not session:
            raise HTTPException(404)
        session.completed_at = datetime.now(timezone.utc)
        await db.commit()

    await _notify_all("trainer", "Your trainee completed their workout! Use /report to see results.")
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# History endpoints
# ---------------------------------------------------------------------------

@router.get("/history")
@limiter.limit("30/minute")
async def get_history(request: Request, current_user: int = Depends(require_trainee)):
    async with async_session() as db:
        result = await db.execute(
            select(WorkoutSession)
            .where(WorkoutSession.trainee_telegram_id == current_user)
            .where(WorkoutSession.completed_at.is_not(None))
            .options(selectinload(WorkoutSession.workout).selectinload(Workout.exercises))
            .order_by(WorkoutSession.completed_at.desc())
        )
        sessions = result.scalars().all()

    return [
        {
            "session_id": s.id,
            "workout_id": s.workout_id,
            "completed_at": _utc_iso(s.completed_at),
            "exercise_count": len(s.workout.exercises),
        }
        for s in sessions
    ]


@router.get("/sessions/{session_id}")
@limiter.limit("30/minute")
async def get_session_detail(request: Request, session_id: int, current_user: int = Depends(require_trainee)):
    async with async_session() as db:
        session = await db.get(
            WorkoutSession,
            session_id,
            options=[
                selectinload(WorkoutSession.workout)
                    .selectinload(Workout.exercises)
                    .selectinload(Exercise.planned_sets),
                selectinload(WorkoutSession.executed_sets),
                selectinload(WorkoutSession.comments),
            ],
        )
        if not session or session.trainee_telegram_id != current_user:
            raise HTTPException(404)

        # Find previous completed session for the same workout
        prev_result = await db.execute(
            select(WorkoutSession)
            .where(WorkoutSession.workout_id == session.workout_id)
            .where(WorkoutSession.trainee_telegram_id == current_user)
            .where(WorkoutSession.completed_at < session.completed_at)
            .where(WorkoutSession.completed_at.is_not(None))
            .options(selectinload(WorkoutSession.executed_sets))
            .order_by(WorkoutSession.completed_at.desc())
            .limit(1)
        )
        prev_session = prev_result.scalar_one_or_none()

    executed = {es.planned_set_id: es for es in session.executed_sets}
    prev_executed = {es.planned_set_id: es for es in prev_session.executed_sets} if prev_session else {}
    comments = {c.exercise_id: c.comment for c in session.comments}

    return {
        "session_id": session.id,
        "completed_at": _utc_iso(session.completed_at),
        "workout": {
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
                            "executed": _fmt_executed(executed.get(ps.id)),
                            "previous": _fmt_executed(prev_executed.get(ps.id)),
                        }
                        for ps in ex.planned_sets
                    ],
                }
                for ex in session.workout.exercises
            ]
        },
    }


def _fmt_executed(es: ExecutedSet | None) -> dict | None:
    if es is None:
        return None
    return {"reps": es.actual_reps, "weight": es.actual_weight}

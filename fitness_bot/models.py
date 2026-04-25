from datetime import datetime
from sqlalchemy import ForeignKey, Text, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Workout(Base):
    __tablename__ = "workouts"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    is_published: Mapped[bool] = mapped_column(default=False)

    exercises: Mapped[list["Exercise"]] = relationship(
        back_populates="workout", order_by="Exercise.order"
    )
    sessions: Mapped[list["WorkoutSession"]] = relationship(back_populates="workout")


class Exercise(Base):
    __tablename__ = "exercises"

    id: Mapped[int] = mapped_column(primary_key=True)
    workout_id: Mapped[int] = mapped_column(ForeignKey("workouts.id"))
    description: Mapped[str] = mapped_column(Text)
    order: Mapped[int]

    workout: Mapped["Workout"] = relationship(back_populates="exercises")
    planned_sets: Mapped[list["PlannedSet"]] = relationship(
        back_populates="exercise", order_by="PlannedSet.set_number"
    )


class PlannedSet(Base):
    __tablename__ = "planned_sets"

    id: Mapped[int] = mapped_column(primary_key=True)
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercises.id"))
    set_number: Mapped[int]
    reps: Mapped[int | None]
    weight: Mapped[float | None]

    exercise: Mapped["Exercise"] = relationship(back_populates="planned_sets")
    executed_sets: Mapped[list["ExecutedSet"]] = relationship(back_populates="planned_set")


class WorkoutSession(Base):
    __tablename__ = "workout_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    workout_id: Mapped[int] = mapped_column(ForeignKey("workouts.id"))
    trainee_telegram_id: Mapped[int]
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    workout: Mapped["Workout"] = relationship(back_populates="sessions")
    executed_sets: Mapped[list["ExecutedSet"]] = relationship(back_populates="session")
    comments: Mapped[list["ExerciseComment"]] = relationship(back_populates="session")


class ExecutedSet(Base):
    __tablename__ = "executed_sets"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("workout_sessions.id"))
    planned_set_id: Mapped[int] = mapped_column(ForeignKey("planned_sets.id"))
    actual_reps: Mapped[int | None]
    actual_weight: Mapped[float | None]

    session: Mapped["WorkoutSession"] = relationship(back_populates="executed_sets")
    planned_set: Mapped["PlannedSet"] = relationship(back_populates="executed_sets")


class ExerciseComment(Base):
    __tablename__ = "exercise_comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("workout_sessions.id"))
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercises.id"))
    comment: Mapped[str] = mapped_column(Text)

    session: Mapped["WorkoutSession"] = relationship(back_populates="comments")
    exercise: Mapped["Exercise"] = relationship()

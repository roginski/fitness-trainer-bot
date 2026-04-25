from .models import WorkoutSession


def format_report(session: WorkoutSession) -> str:
    completed = session.completed_at.strftime("%Y-%m-%d %H:%M") if session.completed_at else "in progress"
    lines = [f"Workout Report — {completed}\n"]

    executed_by_planned = {es.planned_set_id: es for es in session.executed_sets}
    comment_by_exercise = {c.exercise_id: c.comment for c in session.comments}

    for i, exercise in enumerate(session.workout.exercises, 1):
        lines.append(f"{i}. {exercise.description}")
        for ps in exercise.planned_sets:
            planned = _fmt(ps.reps, ps.weight)
            es = executed_by_planned.get(ps.id)
            if es:
                actual = _fmt(es.actual_reps, es.actual_weight)
                lines.append(f"   Set {ps.set_number}: {planned} → {actual}")
            else:
                lines.append(f"   Set {ps.set_number}: {planned} → not logged")
        if exercise.id in comment_by_exercise:
            lines.append(f"   💬 {comment_by_exercise[exercise.id]}")
        lines.append("")

    return "\n".join(lines).strip()


def _fmt(reps: int | None, weight: float | None) -> str:
    if reps is None and weight is None:
        return "—"
    parts = []
    if reps is not None:
        parts.append(f"{reps} reps")
    if weight is not None:
        parts.append(f"{weight}kg")
    return " @ ".join(parts)

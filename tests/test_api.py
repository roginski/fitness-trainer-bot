from tests.conftest import TRAINER_H, TRAINEE_H


# ---------------------------------------------------------------------------
# Trainer endpoints
# ---------------------------------------------------------------------------

async def test_trainer_creates_draft(client):
    r = await client.get("/api/workout/draft", headers=TRAINER_H)
    assert r.status_code == 200
    data = r.json()
    assert "workout_id" in data
    assert data["exercises"] == []


async def test_trainer_second_call_returns_same_draft(client):
    r1 = await client.get("/api/workout/draft", headers=TRAINER_H)
    r2 = await client.get("/api/workout/draft", headers=TRAINER_H)
    assert r1.json()["workout_id"] == r2.json()["workout_id"]


async def test_trainer_adds_exercise(client):
    r = await client.get("/api/workout/draft", headers=TRAINER_H)
    workout_id = r.json()["workout_id"]

    r = await client.post(
        f"/api/workout/{workout_id}/exercises",
        json={"description": "Bench Press", "sets": [{"reps": 8, "weight": 60.0}, {"reps": 8, "weight": 60.0}]},
        headers=TRAINER_H,
    )
    assert r.status_code == 200
    exercises = r.json()["exercises"]
    assert len(exercises) == 1
    assert exercises[0]["description"] == "Bench Press"
    assert len(exercises[0]["planned_sets"]) == 2


async def test_trainer_deletes_exercise(client):
    r = await client.get("/api/workout/draft", headers=TRAINER_H)
    workout_id = r.json()["workout_id"]

    r = await client.post(
        f"/api/workout/{workout_id}/exercises",
        json={"description": "Squat", "sets": [{"reps": 5}]},
        headers=TRAINER_H,
    )
    ex_id = r.json()["exercises"][0]["id"]

    r = await client.delete(f"/api/exercises/{ex_id}", headers=TRAINER_H)
    assert r.status_code == 200
    assert r.json()["exercises"] == []


# ---------------------------------------------------------------------------
# Full end-to-end flow
# ---------------------------------------------------------------------------

async def test_full_workout_flow(client):
    # Trainer: create draft and add exercise
    r = await client.get("/api/workout/draft", headers=TRAINER_H)
    workout_id = r.json()["workout_id"]

    r = await client.post(
        f"/api/workout/{workout_id}/exercises",
        json={"description": "Pull-ups", "sets": [{"reps": 10}, {"reps": 8}]},
        headers=TRAINER_H,
    )
    assert r.status_code == 200
    planned_set_ids = [ps["id"] for ps in r.json()["exercises"][0]["planned_sets"]]

    # Trainer: publish
    r = await client.post(f"/api/workout/{workout_id}/publish", json={}, headers=TRAINER_H)
    assert r.status_code == 200
    assert r.json()["status"] == "published"

    # Trainee: get current workout — creates a session
    r = await client.get("/api/workout/current", headers=TRAINEE_H)
    assert r.status_code == 200
    data = r.json()
    session_id = data["session_id"]
    exercise_id = data["workout"]["exercises"][0]["id"]
    assert len(data["workout"]["exercises"][0]["planned_sets"]) == 2

    # Trainee: log sets
    for ps_id in planned_set_ids:
        r = await client.post(
            "/api/sets/log",
            json={"session_id": session_id, "planned_set_id": ps_id, "actual_reps": 9},
            headers=TRAINEE_H,
        )
        assert r.status_code == 200

    # Trainee: logged data is returned on next fetch
    r = await client.get("/api/workout/current", headers=TRAINEE_H)
    sets = r.json()["workout"]["exercises"][0]["planned_sets"]
    assert all(s["executed"] is not None for s in sets)
    assert all(s["executed"]["reps"] == 9 for s in sets)

    # Trainee: add comment
    r = await client.post(
        "/api/comments",
        json={"session_id": session_id, "exercise_id": exercise_id, "comment": "Felt great"},
        headers=TRAINEE_H,
    )
    assert r.status_code == 200

    # Trainee: complete
    r = await client.post(f"/api/sessions/{session_id}/complete", json={}, headers=TRAINEE_H)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


async def test_no_workout_before_publish(client):
    r = await client.get("/api/workout/current", headers=TRAINEE_H)
    assert r.status_code == 200
    assert r.json()["workout"] is None


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

async def test_unauthenticated_returns_401(client):
    r = await client.get("/api/workout/draft")
    assert r.status_code == 401

    r = await client.get("/api/workout/current")
    assert r.status_code == 401


async def test_trainee_cannot_use_trainer_endpoints(client):
    r = await client.get("/api/workout/draft", headers=TRAINEE_H)
    assert r.status_code == 403


async def test_trainer_cannot_use_trainee_endpoints(client):
    r = await client.get("/api/workout/current", headers=TRAINER_H)
    assert r.status_code == 403

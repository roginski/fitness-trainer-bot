# Fitness Trainer Bot — Project Plan

## What's Done

- [x] Trainer Mini App: create workout, add exercises with sets, delete exercises, publish
- [x] Trainee Mini App: view exercises, log actual reps/weight per set, add comments, complete
- [x] Bot `/report` command: plain text summary of latest completed session
- [x] Trainer/trainee notifications via Telegram bot messages (publish → notify trainee, complete → notify trainer)
- [x] Bot FSM flows (classic chat-based) mirroring the Mini App flows
- [x] FastAPI REST API backing both Mini Apps
- [x] SQLAlchemy models: Workout, Exercise, PlannedSet, WorkoutSession, ExecutedSet, ExerciseComment
- [x] Local dev with ngrok for Telegram Mini App

---

## Phase 1 — Security & Correctness (before sharing with anyone)

- [ ] **Validate Telegram init data** in API: verify the `initData` signature sent by Mini Apps using HMAC-SHA256, so user identity can't be spoofed
- [ ] **Remove `user_id` from request bodies** once init data validation is in place — derive it from verified init data instead
- [ ] **Add Alembic** for database migrations so schema changes don't require manual DB wipes

---

## Phase 2 — Multi-User Support

- [ ] **Support multiple trainer-trainee pairs**: replace hardcoded TRAINER_ID/TRAINEE_ID env vars with a roles table or a registration flow
- [ ] **Trainer registration flow**: `/register_trainer` command or invite-link-based setup
- [ ] **Trainee invite**: trainer can generate a one-time link for a trainee to join

---

## Phase 3 — Workout History & Progress

- [ ] **Workout history for trainee**: list of past sessions with dates in the Mini App
- [ ] **Historical report for trainer**: `/report` shows last N sessions, or a Mini App history view
- [ ] **Progress comparison**: highlight when trainee improved reps/weight vs. prior session

---

## Phase 4 — UX Polish

- [ ] **Edit published workout**: allow trainer to modify exercises/sets after publishing (triggers re-notification to trainee)
- [ ] **Exercise reordering**: drag-and-drop or up/down buttons in trainer Mini App
- [ ] **Error handling in Mini Apps**: retry on network failure, clear error messages on API errors
- [ ] **Local time display**: show session timestamps in user's local timezone
- [ ] **Rest timer**: optional countdown timer between sets in trainee Mini App

---

## Phase 5 — Production Readiness

- [ ] **Tests**: unit tests for API endpoints; integration test for the full workout → session → report flow
- [ ] **Logging**: structured logs with user actions and errors
- [ ] **Rate limiting** on API endpoints
- [ ] **Input validation**: max lengths on descriptions and comments
- [ ] **Deployment**: move off ngrok; deploy FastAPI to a real host (e.g., Railway, Fly.io, VPS)

---

## Out of Scope (for now)

- Video/image exercise guides
- Muscle group tagging / workout categorization
- Data export (CSV/PDF)
- Multiple trainees per workout session

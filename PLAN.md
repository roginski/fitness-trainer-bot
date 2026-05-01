# Fitness Trainer Bot — Project Plan

## Done

- [x] Trainer Mini App: create workout, add/delete/reorder exercises, inline set editing, publish
- [x] Trainee Mini App: view exercises, log actual reps/weight per set, add comments, complete
- [x] Bot `/report` command: plain text summary of last 3 sessions with ↑/↓ comparison
- [x] Bot `/register` command: first user becomes trainer, second becomes trainee
- [x] Bot `/open` command: generates 24-hour token for Telegram Desktop access
- [x] Trainer/trainee notifications (publish → notify trainee, complete → notify trainer)
- [x] FastAPI REST API backing both Mini Apps
- [x] SQLAlchemy models + Alembic migrations
- [x] Telegram init data HMAC-SHA256 verification
- [x] Bot-issued token auth (for Telegram Desktop where initData is empty)
- [x] Workout history tab in trainee Mini App with progress comparison (↑/↓ vs prior session)
- [x] Edit published workout + notify trainee of changes
- [x] Drag-and-drop exercise reordering (SortableJS, self-hosted)
- [x] Tests: unit + integration coverage for API, auth, and token paths

---

## Phase 4 — UX Polish (remaining)

- [ ] **Error handling in Mini Apps**: show clear error messages on API failures, retry on network error
- [ ] **Local time display**: show session timestamps in user's local timezone
- [ ] **Rest timer**: optional countdown timer between sets in trainee Mini App

---

## Phase 5 — Production Readiness

- [ ] **Rate limiting** on API endpoints
- [ ] **Input validation**: max lengths on descriptions and comments
- [ ] **Deployment**: move off ngrok; deploy to a real host (Railway, Fly.io, VPS)

---

## Out of Scope (for now)

- Video/image exercise guides
- Muscle group tagging / workout categorization
- Data export (CSV/PDF)
- Multiple trainees per workout session

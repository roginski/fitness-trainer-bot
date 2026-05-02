# Fitness Trainer Bot

A Telegram bot + Mini App for personal trainer and trainee. The trainer builds workouts in a web UI; the trainee logs sets and tracks progress session-over-session.

## Features

- **Trainer Mini App** — create workouts, add/reorder/delete exercises, edit sets inline, publish
- **Trainee Mini App** — log actual reps and weight per set, add comments, complete workout, view history with ↑/↓ progress comparison
- **Bot commands** — `/register`, `/report` (last 3 sessions summary), `/open` (24h token for Telegram Desktop)
- **Notifications** — trainee notified on publish, trainer notified on completion
- Auth via Telegram `initData` HMAC-SHA256; bot-issued token fallback for Telegram Desktop

## Stack

- Python 3.13, FastAPI, aiogram 3, SQLAlchemy (async), Alembic
- PostgreSQL in production, SQLite for local dev
- SortableJS (self-hosted) for drag-and-drop exercise reordering

## Local setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Create `.env`:

```
BOT_TOKEN=your_telegram_bot_token
TRAINER_ID=your_telegram_id
TRAINEE_ID=trainee_telegram_id
WEBAPP_URL=https://your-ngrok-or-host.com
DEBUG=true
```

Run:

```bash
python main.py
```

Migrations run automatically on startup. For local dev the app uses SQLite (`fitness.db`).

## Deployment (Railway)

1. Create a Railway project, add a PostgreSQL service
2. Connect this repo — Railway sets `DATABASE_URL` automatically
3. Set env vars: `BOT_TOKEN`, `WEBAPP_URL` (your Railway public URL)

## Running tests

```bash
pytest tests/
```

# Commands

## Run the bot

```bash
source .venv/bin/activate && python main.py
```

ngrok must be running separately and `WEBAPP_URL` set in `.env` for Mini Apps to work.

## ngrok

```bash
ngrok http 8000
# then set WEBAPP_URL=https://xxxx.ngrok.io in .env
# then send /start to the bot to re-register the menu button
```

## Tests

```bash
python -m pytest tests/ -v       # all tests, verbose
python -m pytest tests/ -x       # stop on first failure
python -m pytest tests/test_auth.py                        # one file
python -m pytest tests/test_api.py::test_full_workout_flow # one test
```

## Migrations

```bash
alembic upgrade head                              # apply all pending migrations
alembic revision --autogenerate -m "description" # generate migration from model changes
alembic downgrade -1                              # roll back one migration
alembic current                                   # show current migration version
```

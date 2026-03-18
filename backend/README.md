# My Albert Backend

FastAPI backend for the personal student app "My Albert".

It wraps the Albert School Inside API and Google Calendar behind a small REST API that a separate Loveable frontend can call safely. Albert and Google credentials stay server-side only.

## What It Does

- Fetches the Albert profile first and derives the correct `user_id` and `student_id`.
- Exposes frontend-friendly endpoints such as `/api/profile`, `/api/dashboard`, and `/api/planner`.
- Normalizes Albert payloads instead of returning raw upstream responses everywhere.
- Handles partial upstream failure gracefully, especially for grades and Google Calendar.
- Supports an optional fixture mode using the existing `inside_export/` JSON exports for offline/local development.

## Folder Structure

```text
backend/
  app/
    main.py
    core/
    api/
      deps.py
      routes/
    services/
      albert/
      google/
    models/
    utils/
  .env.example
  requirements.txt
  README.md
```

## Setup

1. Create a virtual environment and install dependencies.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Copy the env example and fill in the secrets.

```bash
cp .env.example .env
```

3. Configure Albert.

- Set `ALBERT_BASE_URL=https://api-inside.albertschool.com`
- Set `ALBERT_BEARER_TOKEN` to your Albert token

4. Configure Google Calendar if you want calendar endpoints enabled.

- Set `GOOGLE_CALENDAR_ENABLED=true`
- Put your Google OAuth client secret JSON in a gitignored location
- Set `GOOGLE_CLIENT_SECRET_FILE` to that file path
- On the first calendar request, the backend will complete the local OAuth flow and store a token in `backend/.secrets/google_token.json` unless you change `GOOGLE_TOKEN_FILE`

5. Optional: run in fixture mode without live Albert calls.

- Set `ALBERT_USE_FIXTURES=true`
- Keep `ALBERT_FIXTURES_DIR=../inside_export`

## Run Locally

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

Open:

- `http://localhost:8000/docs`
- `http://localhost:8000/health`

## API Endpoints

- `GET /api/profile`
- `GET /api/cohorts`
- `GET /api/intake`
- `GET /api/courses`
- `GET /api/course-instances`
- `GET /api/course-instances/{id}`
- `GET /api/course-modules/{id}`
- `GET /api/exams`
- `GET /api/attendance`
- `GET /api/transcripts`
- `GET /api/grades`
- `GET /api/calendar/events`
- `GET /api/dashboard`
- `GET /api/planner`

## Response Notes

- `/api/dashboard` aggregates profile, exams, attendance, transcript count, and calendar preview.
- `/api/planner` merges upcoming exams with Google Calendar events into one timeline.
- `/api/grades` returns a structured unavailable state instead of crashing if the Albert grade service fails.
- `/api/calendar/events` returns a structured unavailable state when Google Calendar is disabled or not configured.

## Loveable Frontend Integration

Point the frontend to this backend base URL during local development:

```text
http://localhost:8000
```

Typical frontend calls:

- `GET http://localhost:8000/api/dashboard`
- `GET http://localhost:8000/api/planner`
- `GET http://localhost:8000/api/course-instances`

If the Loveable frontend uses an env variable, set something like:

```text
VITE_API_BASE_URL=http://localhost:8000
```

## Deployment Direction

This backend is ready for a standard FastAPI deployment later on Render, Railway, Fly.io, or a container platform.

For deployment:

- Keep Albert and Google secrets in platform env vars or a secret store
- Replace local Google OAuth bootstrap with a deployment-friendly credential flow if needed
- Run with a production ASGI server config around Uvicorn

## Security Notes

- Do not send Albert bearer tokens or Google credentials to the frontend.
- Keep `.env`, Google token files, and OAuth client secrets out of version control.
- The existing notebook and root-level secret files in this workspace should be rotated or moved to a safer location before publishing or sharing the project.

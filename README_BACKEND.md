# SECTORIQ AI — Backend Phase 1

This version adds a real local SQLite database and separates intelligence logic from Flask routes.

## Start

```bash
python -m venv venv
venv\\Scripts\\activate
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`.

## Backend layers

- `app.py` — Flask application and REST endpoints
- `database/db.py` — SQLite schema + seed data
- `services/intelligence.py` — event impact, forecast and recommendation logic
- `sectoriq.db` — created automatically on first run

## API endpoints

- `/api/health`
- `/api/dashboard`
- `/api/events`
- `/api/locations`
- `/api/impact?event=Diwali%20Festival`
- `/api/forecast`
- `/api/recommendations`
- `/api/search?q=Diwali`

## Next phase

Connect real Calendar and Weather services, then replace the demo forecasting formula with a trained forecasting model. Keep seeded data as a fallback for demo reliability.

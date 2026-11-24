# Python project backend

This backend serves the existing frontend and exposes the JSON endpoints its JavaScript requests. It uses only Python's standard library and SQLite.

## Run

From the project root:

```powershell
python -m Backend
```

Open `http://127.0.0.1:8000/`. The root URL serves `Frontend/index.html`; existing relative URLs such as `/pages/plan.html` and `/css/styles.css` are mapped to the `Frontend/` folder. The database is created at `Backend/app.sqlite3` on first start.

## Files

- `server.py`: local HTTP server, frontend static files, and JSON response helpers.
- `api.py`: route handlers and request validation for all screens.
- `database.py`: SQLite connection and schema initialization.
- `services.py`: profile, plan, dashboard, and report calculations.
- `data.py`: frontend JSON loading and assessment option data.
- `config.py`: shared paths and server settings.

## API routes

| Method | Route | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Check the server |
| GET, POST | `/api/assessment/options`, `/api/assessment/start` | Load and save skill assessment |
| GET, POST | `/api/career/options`, `/api/career/assessment` | Load and save career profile |
| GET | `/api/career/recommendations` | Get career matches |
| GET, PATCH | `/api/dashboard`, `/api/tasks/{id}` | Dashboard data and task state |
| GET, PATCH, POST | `/api/plan`, `/api/plan/items/{id}`, `/api/plan/schedule` | Learning plan and progress |
| GET, POST | `/api/practice/questions`, `/api/practice/answers` | Quiz questions and answer submissions |
| GET, POST | `/api/practice/warmups`, `/api/practice/focus-sessions` | Interview prompts and focus sessions |
| GET, POST | `/api/practice/reviews`, `/api/practice/reviews/{id}/start` | Review queue |
| GET | `/api/reports` | Progress summary |

Each browser gets a persistent anonymous ID cookie; stored progress is scoped to that browser. No account or sign-in screen is present in the supplied frontend, so this backend does not implement account management.

## Integration notes

The backend reads `Frontend/data/questions.json`, `learning-plan.json`, and `interview-prompts.json` directly. Keep those file names and fields intact or update `Backend/data.py` to match. The career page endpoints are available, but the screenshot's `career-results.html` and `career-results.js` must send `GET /api/career/options`, `POST /api/career/assessment`, and `GET /api/career/recommendations` using the field names shown in `api.py`.

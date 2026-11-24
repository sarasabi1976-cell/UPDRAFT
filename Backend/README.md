# Python project backend (Flask)

This backend uses Flask for HTTP routing, serves the existing frontend, and stores user progress in SQLite. The existing `/api/...` endpoints and browser-cookie account flow are preserved.

## Run

From the project root in PowerShell:

```powershell
python -m pip install -r Backend/requirements.txt
python -m Backend
```

Open `http://127.0.0.1:8000/`. Flask serves `Frontend/index.html` at the root and maps existing URLs such as `/pages/plan.html` and `/css/styles.css` to the `Frontend/` directory. The database is created at `Backend/app.sqlite3` on first start.

## Files

- `app.py`: Flask application, frontend file serving, and compatibility adapter for existing API handlers.
- `server.py`: application entry point used by `python -m Backend`.
- `api.py`: route handlers and request validation for all screens.
- `database.py`: SQLite connection and schema initialization.
- `services.py`: profile, plan, dashboard, and report calculations.
- `data.py`: frontend JSON loading and assessment option data.
- `config.py`: shared paths and server settings.

## API routes

| Method | Route | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Check the server |
| GET, POST | `/api/auth/me`, `/api/auth/register`, `/api/auth/login`, `/api/auth/logout`, `/api/auth/activity` | Accounts, switching users, and activity history |
| GET, POST | `/api/assessment/options`, `/api/assessment/start` | Load and save skill assessment |
| GET, POST | `/api/career/options`, `/api/career/assessment` | Load and save career profile |
| GET | `/api/career/recommendations` | Get career matches |
| GET, PATCH | `/api/dashboard`, `/api/tasks/{id}` | Dashboard data and task state |
| GET, PATCH, POST | `/api/plan`, `/api/plan/items/{id}`, `/api/plan/schedule` | Learning plan and progress |
| GET, POST | `/api/practice/questions`, `/api/practice/answers` | Quiz questions and answer submissions |
| GET, POST | `/api/practice/warmups`, `/api/practice/focus-sessions` | Interview prompts and focus sessions |
| GET, POST | `/api/practice/reviews`, `/api/practice/reviews/{id}/start` | Review queue |
| GET | `/api/reports` | Progress summary |
| GET | `/api/jobs/search` | Latest vacancies and personalized LinkedIn search URL |

Guest progress is stored per browser. Users can create an account from the Account / Switch user page; registration upgrades the current guest profile so its progress is retained. Passwords are PBKDF2-HMAC-SHA256 hashes with unique salts, and signed-in sessions use HttpOnly cookies that expire after 30 days. API activity and successful login/logout events are stored per user. Reports can be printed or saved as PDF using the browser's print dialog.

## Integration notes

The backend reads `Frontend/data/questions.json`, `learning-plan.json`, `interview-prompts.json`, and `career-paths.json`. Add quiz records with `id`, `question`, `options`, and the correct option text in `answer`; add plan items under each week's `activities`. Career choices and rule-based recommendation paths come from `career-paths.json`. This is a defined supported catalog, not arbitrary unvalidated input. Answers, focus sessions, and readiness snapshots are stored in SQLite; weekly charts use dated records.

## Latest jobs

The LinkedIn Jobs page opens LinkedIn's own search results for live LinkedIn vacancies. LinkedIn's public Job Posting API is restricted to approved partners and is for submitting/managing postings, not a general job-search feed. The page also supports in-page listings through Adzuna's documented search API. Register for an Adzuna API app ID and key, then set them in the same PowerShell terminal before starting the backend:

```powershell
$env:ADZUNA_APP_ID = "your-app-id"
$env:ADZUNA_APP_KEY = "your-app-key"
python -m Backend
```

Without Adzuna credentials, the page still generates a live LinkedIn search link; in-page vacancy cards remain unavailable until a feed is configured.

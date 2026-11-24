from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_ROOT = PROJECT_ROOT / "Frontend"
DATA_ROOT = FRONTEND_ROOT / "data"
DB_PATH = Path(__file__).resolve().parent / "app.sqlite3"
HOST = "127.0.0.1"
PORT = 8000

QUESTIONS_PATH = DATA_ROOT / "questions.json"
PLAN_PATH = DATA_ROOT / "learning-plan.json"
PROMPTS_PATH = DATA_ROOT / "interview-prompts.json"

CAREER_DATA_PATH = DATA_ROOT / "career-paths.json"

# Optional credentials for the in-page latest job feed (Adzuna API).
import os
ADZUNA_APP_ID = os.environ.get("ADZUNA_APP_ID", "").strip()
ADZUNA_APP_KEY = os.environ.get("ADZUNA_APP_KEY", "").strip()

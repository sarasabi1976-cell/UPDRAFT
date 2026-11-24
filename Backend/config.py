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

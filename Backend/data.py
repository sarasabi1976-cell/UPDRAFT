import json
from .config import QUESTIONS_PATH, PLAN_PATH, PROMPTS_PATH, CAREER_DATA_PATH

def read_json(path, default):
    try: return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError): return default

def questions(): return read_json(QUESTIONS_PATH, [])
def plan_data(): return read_json(PLAN_PATH, {"title": "Interview preparation", "durationWeeks": 4, "weeks": []})
def prompts(): return read_json(PROMPTS_PATH, [])
def career_catalog(): return read_json(CAREER_DATA_PATH, {"degrees": [], "skills": [], "paths": []})

_CAREER_CATALOG = career_catalog()
CAREER_DEGREES = _CAREER_CATALOG.get("degrees", [])
CAREER_SKILLS = _CAREER_CATALOG.get("skills", [])
CAREER_PATHS = _CAREER_CATALOG.get("paths", [])
ROLES = [{"id": x, "label": x} for x in ["Software Engineer", "Frontend Developer", "Backend Developer", "Data Analyst", "Product Manager"]]
LEVELS = [{"id": x, "label": x} for x in ["Entry level", "Mid level", "Senior level"]]
SKILLS = [{"id": x, "label": x} for x in ["Problem solving", "Data structures", "System design", "Communication", "Behavioral interviews"]]

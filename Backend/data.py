import json
from .config import QUESTIONS_PATH, PLAN_PATH, PROMPTS_PATH

ROLES = [{"id": x, "label": x} for x in ["Software Engineer", "Frontend Developer", "Backend Developer", "Data Analyst", "Product Manager"]]
LEVELS = [{"id": x, "label": x} for x in ["Entry level", "Mid level", "Senior level"]]
SKILLS = [{"id": x, "label": x} for x in ["Problem solving", "Data structures", "System design", "Communication", "Behavioral interviews"]]
CAREER_DEGREES = [
    {"id": "computer-science", "label": "Computer Science", "specializations": [{"id": "software", "label": "Software Engineering"}, {"id": "data", "label": "Data Science"}]},
    {"id": "information-technology", "label": "Information Technology", "specializations": [{"id": "web", "label": "Web Development"}, {"id": "security", "label": "Cybersecurity"}]},
    {"id": "business", "label": "Business", "specializations": [{"id": "product", "label": "Product Management"}, {"id": "analytics", "label": "Business Analytics"}]},
]
CAREER_SKILLS = [{"id": x, "label": x.replace("-", " ").title()} for x in ["python", "javascript", "sql", "communication", "problem-solving", "system-design"]]


def read_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def questions(): return read_json(QUESTIONS_PATH, [])
def plan_data(): return read_json(PLAN_PATH, {"title": "Interview preparation", "durationWeeks": 4, "topics": []})
def prompts(): return read_json(PROMPTS_PATH, [])

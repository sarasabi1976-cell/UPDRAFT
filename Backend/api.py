import json
import re
import secrets
from datetime import date, timedelta
from http.cookies import SimpleCookie
from urllib.parse import unquote, urlsplit

from .data import CAREER_DEGREES, CAREER_SKILLS, LEVELS, ROLES, SKILLS, questions, prompts
from .database import connect
from .services import aggregate, build_plan, clamp, dashboard, now, user_profile


class API:
    """HTTP API handler. JSON shapes here match Frontend/js fetch calls."""
    def __init__(self, handler): self.h = handler

    def respond(self, data, status=200, cookie=None): self.h.respond(data, status, cookie)
    def fail(self, message, status=400): self.respond({"error": message}, status)

    def identity(self):
        cookie = SimpleCookie(self.h.headers.get("Cookie", ""))
        value = cookie.get("updraft_uid")
        if value and re.fullmatch(r"[a-f0-9]{32}", value.value): return value.value, None
        uid = secrets.token_hex(16)
        return uid, uid

    def dispatch(self):
        uid, set_cookie = self.identity()
        path = unquote(urlsplit(self.h.path).path)
        method = self.h.command
        try:
            payload = self.h.read_json() if method in ("POST", "PATCH", "PUT") else {}
            with connect() as db:
                db.execute("INSERT OR IGNORE INTO users(id,name,created_at) VALUES(?,?,?)", (uid, "Guest", now()))
                if path == "/api/health" and method == "GET": return self.respond({"status": "ok", "service": "python-project"}, cookie=set_cookie)
                if path == "/api/assessment/options" and method == "GET": return self.respond({"roles": ROLES, "levels": LEVELS, "skills": SKILLS}, cookie=set_cookie)
                if path == "/api/assessment/start" and method == "POST":
                    role, level, selected = payload.get("roleId"), payload.get("levelId"), payload.get("skillIds")
                    if role not in [x["id"] for x in ROLES] or level not in [x["id"] for x in LEVELS] or not isinstance(selected, list) or not selected or any(x not in [s["id"] for s in SKILLS] for x in selected): return self.fail("Choose a valid role, level, and at least one skill.")
                    db.execute("INSERT INTO profiles(user_id,role_id,level_id,skill_ids) VALUES(?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET role_id=excluded.role_id,level_id=excluded.level_id,skill_ids=excluded.skill_ids", (uid, role, level, json.dumps(selected)))
                    build_plan(db, uid)
                    return self.respond({"nextUrl": "/pages/practice.html"}, 201, set_cookie)
                if path == "/api/career/options" and method == "GET": return self.respond({"degrees": CAREER_DEGREES, "skills": CAREER_SKILLS}, cookie=set_cookie)
                if path == "/api/career/assessment" and method == "POST":
                    degree, spec, ratings = payload.get("degreeId"), payload.get("specializationId"), payload.get("skills")
                    valid_specs = {s["id"] for d in CAREER_DEGREES for s in d["specializations"]}
                    if degree not in {d["id"] for d in CAREER_DEGREES} or spec not in valid_specs or not isinstance(ratings, dict) or any(not isinstance(v, int) or isinstance(v, bool) or not 1 <= v <= 5 for v in ratings.values()): return self.fail("Provide valid education and skill ratings.")
                    profile = user_profile(db, uid)
                    career = {"degreeId": degree, "specializationId": spec, "studyYear": str(payload.get("studyYear", "")), "skills": ratings}
                    db.execute("INSERT INTO profiles(user_id,role_id,level_id,skill_ids,career_data) VALUES(?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET career_data=excluded.career_data", (uid, profile.get("roleId"), profile.get("levelId"), json.dumps(profile.get("skillIds", [])), json.dumps(career)))
                    return self.respond({"saved": True}, 201, set_cookie)
                if path == "/api/career/recommendations" and method == "GET": return self.respond(self.career_recommendations(user_profile(db, uid).get("career")), cookie=set_cookie)
                if path == "/api/dashboard" and method == "GET": return self.respond(dashboard(db, uid), cookie=set_cookie)
                match = re.fullmatch(r"/api/tasks/([^/]+)", path)
                if match and method == "PATCH":
                    task_id = match.group(1)
                    if task_id not in {"daily-quiz", "review-plan", "warmup"} or not isinstance(payload.get("completed"), bool): return self.fail("Unknown task or invalid completion value.", 404)
                    db.execute("INSERT INTO task_state(user_id,task_id,completed) VALUES(?,?,?) ON CONFLICT(user_id,task_id) DO UPDATE SET completed=excluded.completed", (uid, task_id, int(payload["completed"])))
                    return self.respond({"id": task_id, "completed": payload["completed"]}, cookie=set_cookie)
                if path == "/api/plan" and method == "GET": return self.respond(build_plan(db, uid), cookie=set_cookie)
                match = re.fullmatch(r"/api/plan/items/([^/]+)", path)
                if match and method == "PATCH":
                    if not isinstance(payload.get("completed"), bool): return self.fail("completed must be a boolean")
                    cur = db.execute("UPDATE plan_items SET completed=? WHERE id=? AND user_id=?", (int(payload["completed"]), match.group(1), uid))
                    if not cur.rowcount: return self.fail("Plan item not found.", 404)
                    return self.respond({"id": match.group(1), "completed": payload["completed"]}, cookie=set_cookie)
                if path == "/api/plan/schedule" and method == "POST": return self.respond({"editUrl": "/pages/plan.html?edit=1"}, cookie=set_cookie)
                if path == "/api/practice/questions" and method == "GET":
                    return self.respond({"questions": [{"id": q["id"], "prompt": q["question"], "options": [{"id": str(i), "text": text} for i, text in enumerate(q.get("options", []))]} for q in questions()]}, cookie=set_cookie)
                if path == "/api/practice/answers" and method == "POST":
                    question = next((q for q in questions() if q["id"] == payload.get("questionId")), None)
                    if not question: return self.fail("Question not found.", 404)
                    try: answer = int(payload.get("optionId"))
                    except (TypeError, ValueError): return self.fail("Invalid option.")
                    if answer < 0 or answer >= len(question.get("options", [])): return self.fail("Invalid option.")
                    correct = answer == question.get("correctAnswer")
                    db.execute("INSERT INTO answers(user_id,question_id,correct,created_at) VALUES(?,?,?,?)", (uid, question["id"], int(correct), now()))
                    return self.respond({"correct": correct, "explanation": question.get("explanation", "")}, 201, set_cookie)
                if path == "/api/practice/warmups" and method == "GET": return self.respond({"prompts": [{"id": p["id"], "text": p["prompt"]} for p in prompts()]}, cookie=set_cookie)
                if path == "/api/practice/focus-sessions" and method == "POST":
                    duration = payload.get("durationSeconds")
                    if not isinstance(duration, int) or isinstance(duration, bool) or not 60 <= duration <= 7200 or payload.get("completed") is not True: return self.fail("A completed focus session between 1 minute and 2 hours is required.")
                    db.execute("INSERT INTO focus_sessions(user_id,duration_seconds,prompt_id,completed,created_at) VALUES(?,?,?,?,?)", (uid, duration, payload.get("promptId"), 1, now()))
                    return self.respond({"saved": True, "durationSeconds": duration}, 201, set_cookie)
                if path == "/api/practice/reviews" and method == "GET":
                    answers = db.execute("SELECT question_id,MAX(created_at) AS last FROM answers WHERE user_id=? GROUP BY question_id", (uid,)).fetchall()
                    qs = {q["id"]: q for q in questions()}
                    return self.respond({"items": [{"id": a["question_id"], "title": qs[a["question_id"]].get("topic", "Practice review"), "lastPracticed": a["last"][:10], "dueLabel": "Ready to review"} for a in answers if a["question_id"] in qs]}, cookie=set_cookie)
                match = re.fullmatch(r"/api/practice/reviews/([^/]+)/start", path)
                if match and method == "POST":
                    qid = match.group(1)
                    if not any(q["id"] == qid for q in questions()): return self.fail("Review item not found.", 404)
                    db.execute("INSERT INTO reviews(user_id,review_id,started_at) VALUES(?,?,?) ON CONFLICT(user_id,review_id) DO UPDATE SET started_at=excluded.started_at", (uid, qid, now()))
                    return self.respond({"nextUrl": "/pages/practice.html?review=" + qid}, cookie=set_cookie)
                if path == "/api/reports" and method == "GET": return self.respond(self.report(db, uid), cookie=set_cookie)
                if path.startswith("/api/"): return self.fail("API route not found.", 404)
        except (ValueError, json.JSONDecodeError): return self.fail("Request body must be valid JSON.")
        except Exception as exc:
            print(f"API error: {exc}")
            return self.fail("Internal server error.", 500)
        self.h.serve_frontend(path)

    def career_recommendations(self, profile):
        if not profile: return {"matches": []}
        labels = {s["id"]: s["label"] for s in CAREER_SKILLS}
        average = sum(profile["skills"].values()) / max(1, len(profile["skills"]))
        chosen = next((s["label"] for d in CAREER_DEGREES if d["id"] == profile["degreeId"] for s in d["specializations"] if s["id"] == profile["specializationId"]), "Technology")
        required = ["python", "problem-solving", "communication"] if "data" in profile["specializationId"] or "analytics" in profile["specializationId"] else ["javascript", "system-design", "communication"]
        gaps = [labels[x] for x in required if profile["skills"].get(x, 3) < 4]
        return {"matches": [{"title": chosen, "matchPercent": clamp(round(55 + average * 9)), "description": f"A suggested path based on your {chosen.lower()} specialization and self-rated skills.", "requiredSkills": [labels[x] for x in required], "skillGaps": gaps, "studyTasks": [f"Strengthen {g}" for g in gaps] or ["Build a portfolio project", "Practice interview questions"], "links": [{"label": "Explore role skills", "url": "https://www.onetonline.org/"}]}]}

    def report(self, db, uid):
        answers, sessions, profile, plan, accuracy, focus_minutes, readiness = aggregate(db, uid)
        skills = [{"id": skill, "name": next((x["label"] for x in SKILLS if x["id"] == skill), skill), "score": accuracy if answers else None} for skill in profile.get("skillIds", [])]
        wins = []
        if answers: wins.append({"icon": "✓", "title": "Practice answers recorded", "description": f"You have answered {len(answers)} questions with {accuracy}% accuracy."})
        if plan["completed"]: wins.append({"icon": "✧", "title": "Plan progress", "description": f"Completed {plan['completed']} prep plan items."})
        if sessions: wins.append({"icon": "◷", "title": "Focused practice", "description": f"Logged {round(focus_minutes/60,1)} focused hours."})
        return {"metrics": {"readinessScore": readiness, "readinessChange": 0, "readinessPeriod": "points in 30 days", "practiceSessions": len(sessions), "sessionsChange": 0, "sessionsPeriod": "this month", "focusedHours": round(focus_minutes/60, 1), "focusedDays": len({s["created_at"][:10] for s in sessions}), "streakBest": 0, "streakCaption": "Personal best"}, "selectedSkills": skills, "recentWins": wins, "insight": "Small, regular practice sessions help build confidence over time." if answers or sessions else "Start a skill assessment and complete a practice session to see personalized insights."}

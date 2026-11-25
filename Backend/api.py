import hashlib
import hmac
import json
import re
import secrets
import random
from datetime import date, datetime, timedelta, timezone
from http.cookies import SimpleCookie
from urllib.parse import parse_qs, unquote, urlsplit

from .data import CAREER_DEGREES, CAREER_SKILLS, CAREER_PATHS, LEVELS, ROLES, SKILLS, questions, prompts
from .database import connect
from .jobs import search_jobs
from .services import aggregate, build_plan, clamp, dashboard, now, user_profile, report, save_readiness_snapshot


class API:
    """HTTP API handler. JSON shapes here match Frontend/js fetch calls."""
    def __init__(self, handler): self.h = handler

    def respond(self, data, status=200, cookie=None, cookies=None): return self.h.respond(data, status, cookie, cookies)
    def fail(self, message, status=400): return self.respond({"error": message}, status)

    @staticmethod
    def password_hash(password, salt):
        return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), 240_000).hex()

    @staticmethod
    def session_hash(token):
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def create_session(self, db, uid):
        token = secrets.token_hex(32)
        created = now()
        expires = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(timespec="seconds")
        db.execute("INSERT INTO sessions(token_hash,user_id,created_at,expires_at) VALUES(?,?,?,?)", (self.session_hash(token), uid, created, expires))
        return token

    @staticmethod
    def session_cookie(token):
        return f"updraft_session={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age=2592000"

    def record_activity(self, db, uid, action, details=None):
        db.execute("INSERT INTO user_activity(user_id,action,details,created_at) VALUES(?,?,?,?)", (uid, action, json.dumps(details or {}), now()))

    def identity(self):
        cookie = SimpleCookie(self.h.headers.get("Cookie", ""))
        self.session_token = cookie.get("updraft_session").value if cookie.get("updraft_session") else None
        if self.session_token and re.fullmatch(r"[a-f0-9]{64}", self.session_token):
            with connect() as db:
                session = db.execute("SELECT user_id FROM sessions WHERE token_hash=? AND expires_at>?", (self.session_hash(self.session_token), now())).fetchone()
            if session: return session["user_id"], None, True
        value = cookie.get("updraft_uid")
        if value and re.fullmatch(r"[a-f0-9]{32}", value.value): return value.value, None, False
        uid = secrets.token_hex(16)
        return uid, uid, False

    def dispatch(self):
        uid, set_cookie, authenticated = self.identity()
        path = unquote(urlsplit(self.h.path).path)
        method = self.h.command
        try:
            payload = self.h.read_json() if method in ("POST", "PATCH", "PUT") else {}
            with connect() as db:
                db.execute("INSERT OR IGNORE INTO users(id,name,created_at) VALUES(?,?,?)", (uid, "Guest", now()))
                if path == "/api/auth/me" and method == "GET":
                    user = db.execute("SELECT name,username FROM users WHERE id=?", (uid,)).fetchone()
                    return self.respond({"authenticated": bool(authenticated and user["username"]), "user": {"name": user["name"], "username": user["username"]}}, cookie=set_cookie)
                if path == "/api/auth/accounts" and method == "GET":
                    rows = db.execute("SELECT username,name,last_login_at FROM users WHERE username IS NOT NULL ORDER BY lower(name),lower(username)").fetchall()
                    return self.respond({"accounts": [{"username": row["username"], "name": row["name"], "lastLoginAt": row["last_login_at"]} for row in rows]}, cookie=set_cookie)
                if path == "/api/auth/activity" and method == "GET":
                    rows = db.execute("SELECT action,details,created_at FROM user_activity WHERE user_id=? ORDER BY id DESC LIMIT 50", (uid,)).fetchall()
                    return self.respond({"items": [{"action": row["action"], "details": json.loads(row["details"] or "{}"), "createdAt": row["created_at"]} for row in rows]}, cookie=set_cookie)
                if path == "/api/auth/register" and method == "POST":
                    username = str(payload.get("username", "")).strip().lower()
                    password = payload.get("password")
                    display_name = str(payload.get("name", "")).strip()
                    if not re.fullmatch(r"[a-z0-9_.-]{3,32}", username): return self.fail("Username must be 3–32 characters using letters, numbers, dots, underscores, or hyphens.")
                    if not isinstance(password, str) or len(password) < 8: return self.fail("Password must contain at least 8 characters.")
                    if not display_name or len(display_name) > 60: return self.fail("Enter a display name of 1–60 characters.")
                    user = db.execute("SELECT username FROM users WHERE id=?", (uid,)).fetchone()
                    if user and user["username"]: return self.fail("This browser is already signed in. Sign out before creating another account.", 409)
                    if db.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone(): return self.fail("That username is already in use.", 409)
                    salt = secrets.token_hex(16)
                    hashed = self.password_hash(password, salt)
                    db.execute("UPDATE users SET name=?,username=?,password_hash=?,password_salt=?,last_login_at=? WHERE id=?", (display_name, username, hashed, salt, now(), uid))
                    self.record_activity(db, uid, "account_created")
                    self.record_activity(db, uid, "login")
                    token = self.create_session(db, uid)
                    clear_guest = "updraft_uid=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0"
                    return self.respond({"created": True, "user": {"name": display_name, "username": username}}, 201, cookies=[self.session_cookie(token), clear_guest])
                if path == "/api/auth/login" and method == "POST":
                    username = str(payload.get("username", "")).strip().lower()
                    password = payload.get("password")
                    user = db.execute("SELECT id,name,username,password_hash,password_salt FROM users WHERE username=?", (username,)).fetchone()
                    valid = bool(user and isinstance(password, str) and user["password_hash"] and hmac.compare_digest(self.password_hash(password, user["password_salt"]), user["password_hash"]))
                    if not valid: return self.fail("Username or password is incorrect.", 401)
                    uid = user["id"]
                    db.execute("UPDATE users SET last_login_at=? WHERE id=?", (now(), uid))
                    self.record_activity(db, uid, "login")
                    token = self.create_session(db, uid)
                    clear_guest = "updraft_uid=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0"
                    return self.respond({"loggedIn": True, "user": {"name": user["name"], "username": user["username"]}}, cookies=[self.session_cookie(token), clear_guest])
                if path == "/api/auth/logout" and method == "POST":
                    if authenticated and self.session_token:
                        self.record_activity(db, uid, "logout")
                        db.execute("DELETE FROM sessions WHERE token_hash=?", (self.session_hash(self.session_token),))
                    guest_uid = secrets.token_hex(16)
                    db.execute("INSERT OR IGNORE INTO users(id,name,created_at) VALUES(?,?,?)", (guest_uid, "Guest", now()))
                    clear_session = "updraft_session=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0"
                    return self.respond({"loggedOut": True}, cookies=[clear_session], cookie=guest_uid)
                if path == "/api/health" and method == "GET": return self.respond({"status": "ok", "service": "python-project"}, cookie=set_cookie)
                if path.startswith("/api/") and not path.startswith("/api/auth/"):
                    self.record_activity(db, uid, f"{method} {path}")
                if path == "/api/assessment/options" and method == "GET": return self.respond({"roles": ROLES, "levels": LEVELS, "skills": SKILLS}, cookie=set_cookie)
                if path == "/api/assessment/start" and method == "POST":
                    role, level, selected = payload.get("roleId"), payload.get("levelId"), payload.get("skillIds")
                    if role not in [x["id"] for x in ROLES] or level not in [x["id"] for x in LEVELS] or not isinstance(selected, list) or not selected or any(x not in [s["id"] for s in SKILLS] for x in selected): return self.fail("Choose a valid role, level, and at least one skill.")
                    db.execute("INSERT INTO profiles(user_id,role_id,level_id,skill_ids) VALUES(?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET role_id=excluded.role_id,level_id=excluded.level_id,skill_ids=excluded.skill_ids", (uid, role, level, json.dumps(selected)))
                    build_plan(db, uid)
                    save_readiness_snapshot(db, uid)
                    return self.respond({"nextUrl": "/pages/practice.html"}, 201, set_cookie)
                if path == "/api/career/options" and method == "GET": return self.respond({"degrees": CAREER_DEGREES, "skills": CAREER_SKILLS}, cookie=set_cookie)
                if path == "/api/career/assessment" and method == "POST":
                    degree, spec, ratings = payload.get("degreeId"), payload.get("specializationId"), payload.get("skills")
                    selected_degree = next((d for d in CAREER_DEGREES if d["id"] == degree), None)
                    valid_specs = {s["id"] for s in selected_degree["specializations"]} if selected_degree else set()
                    selected_spec = next((s for s in selected_degree["specializations"] if s["id"] == spec), None) if selected_degree else None
                    expected_skills = set(selected_spec.get("skillIds", [])) if selected_spec else set()
                    if not selected_degree or spec not in valid_specs or not expected_skills or not isinstance(ratings, dict) or set(ratings) != expected_skills or any(type(v) is not int or not 1 <= v <= 5 for v in ratings.values()): return self.fail("Rate every skill shown for your chosen specialization from 1 to 5.")
                    profile = user_profile(db, uid)
                    career = {"degreeId": degree, "specializationId": spec, "studyYear": str(payload.get("studyYear", "")), "skills": ratings}
                    db.execute("INSERT INTO profiles(user_id,role_id,level_id,skill_ids,career_data) VALUES(?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET career_data=excluded.career_data", (uid, profile.get("roleId"), profile.get("levelId"), json.dumps(profile.get("skillIds", [])), json.dumps(career)))
                    save_readiness_snapshot(db, uid)
                    return self.respond({"saved": True}, 201, set_cookie)
                if path == "/api/career/recommendations" and method == "GET": return self.respond(self.career_recommendations(user_profile(db, uid).get("career")), cookie=set_cookie)
                if path == "/api/jobs/search" and method == "GET":
                    params = parse_qs(urlsplit(self.h.path).query)
                    result = search_jobs(user_profile(db, uid), params.get("what", [""])[0], params.get("where", [""])[0], params.get("country", ["in"])[0])
                    return self.respond(result, cookie=set_cookie)
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
                    save_readiness_snapshot(db, uid)
                    return self.respond({"id": match.group(1), "completed": payload["completed"]}, cookie=set_cookie)
                if path == "/api/plan/schedule" and method == "POST": return self.respond({"editable": True}, cookie=set_cookie)
                if path == "/api/plan/schedule" and method == "PATCH":
                    items = payload.get("items")
                    if not isinstance(items, list) or not items or len(items) > 100:
                        return self.fail("Provide between 1 and 100 schedule activities.")
                    submitted_ids = [str(item.get("id", "")) for item in items if isinstance(item, dict)]
                    if len(submitted_ids) != len(items) or len(set(submitted_ids)) != len(items):
                        return self.fail("Each schedule activity must have a unique id.")
                    for item in items:
                        title, description, week = item.get("title"), item.get("description", ""), item.get("week")
                        owned = db.execute("SELECT 1 FROM plan_items WHERE id=? AND user_id=?", (str(item["id"]), uid)).fetchone()
                        if not owned:
                            return self.fail("A schedule activity was not found for this account.", 404)
                        if (not isinstance(title, str) or not title.strip() or len(title.strip()) > 120
                                or not isinstance(description, str) or len(description) > 240
                                or not isinstance(week, int) or isinstance(week, bool) or not 1 <= week <= 52):
                            return self.fail("Each activity needs a name, a description of up to 240 characters, and a week from 1 to 52.")
                    db.executemany("UPDATE plan_items SET title=?,description=?,week=? WHERE id=? AND user_id=?", [(item["title"].strip(), item.get("description", "").strip(), item["week"], str(item["id"]), uid) for item in items])
                    save_readiness_snapshot(db, uid)
                    return self.respond({"saved": True, "items": len(items)}, cookie=set_cookie)
                if path == "/api/practice/questions" and method == "GET":
                    relevant = self.practice_questions(user_profile(db, uid))
                    params = parse_qs(urlsplit(self.h.path).query)
                    try: limit = max(1, min(10, int(params.get("limit", ["10"])[0])))
                    except (TypeError, ValueError): limit = 10
                    excluded = {value for value in params.get("exclude", [""])[0].split(",") if value}
                    available = [q for q in relevant if str(q["id"]) not in excluded]
                    restarted = not available and bool(relevant) and bool(excluded)
                    pool = available if available else relevant
                    selected = random.sample(pool, min(limit, len(pool))) if pool else []
                    return self.respond({"questions": [{"id": q["id"], "prompt": q["question"], "topic": q.get("topic", "Practice"), "options": [{"id": str(i), "text": text} for i, text in enumerate(q.get("options", []))]} for q in selected], "restartedRound": restarted}, cookie=set_cookie)
                if path == "/api/practice/answers" and method == "POST":
                    question = next((q for q in self.practice_questions(user_profile(db, uid)) if str(q["id"]) == str(payload.get("questionId"))), None)
                    if not question: return self.fail("Question is not part of your current skill practice.", 404)
                    try: answer = int(payload.get("optionId"))
                    except (TypeError, ValueError): return self.fail("Invalid option.")
                    if answer < 0 or answer >= len(question.get("options", [])): return self.fail("Invalid option.")
                    correct_answer_index = question.get("correctAnswer")
                    if correct_answer_index is not None:
                        correct = answer == int(correct_answer_index)
                    else:
                        correct_answer_text = question.get("answer")
                        selected_answer_text = question["options"][answer]
                        correct = (
                            isinstance(correct_answer_text, str)
                            and selected_answer_text.strip().casefold() == correct_answer_text.strip().casefold()
                        )
                    db.execute("INSERT INTO answers(user_id,question_id,correct,created_at) VALUES(?,?,?,?)", (uid, question["id"], int(correct), now()))
                    save_readiness_snapshot(db, uid)
                    return self.respond({"correct": correct, "explanation": question.get("explanation", "")}, 201, set_cookie)
                if path == "/api/practice/warmups" and method == "GET": return self.respond({"prompts": [{"id": p["id"], "text": p["prompt"]} for p in prompts()]}, cookie=set_cookie)
                if path == "/api/practice/focus-sessions" and method == "POST":
                    duration = payload.get("durationSeconds")
                    completed = payload.get("completed")
                    if not isinstance(duration, int) or isinstance(duration, bool) or not 1 <= duration <= 7200 or not isinstance(completed, bool) or (completed and duration < 60): return self.fail("Focus sessions must be 1 second to 2 hours; completed sessions must be at least 1 minute.")
                    db.execute("INSERT INTO focus_sessions(user_id,duration_seconds,prompt_id,completed,created_at) VALUES(?,?,?,?,?)", (uid, duration, payload.get("promptId"), int(completed), now()))
                    save_readiness_snapshot(db, uid)
                    return self.respond({"saved": True, "durationSeconds": duration, "completed": completed}, 201, set_cookie)
                if path == "/api/practice/reviews" and method == "GET":
                    answers = db.execute("SELECT question_id,MAX(created_at) AS last FROM answers WHERE user_id=? GROUP BY question_id", (uid,)).fetchall()
                    qs = {str(q["id"]): q for q in self.practice_questions(user_profile(db, uid))}
                    return self.respond({"items": [{"id": a["question_id"], "title": qs[str(a["question_id"])].get("topic", "Practice review"), "lastPracticed": a["last"][:10], "dueLabel": "Ready to review"} for a in answers if str(a["question_id"]) in qs]}, cookie=set_cookie)
                match = re.fullmatch(r"/api/practice/reviews/([^/]+)/start", path)
                if match and method == "POST":
                    qid = match.group(1)
                    if not any(str(q["id"]) == qid for q in self.practice_questions(user_profile(db, uid))): return self.fail("Review item is not part of your current skill practice.", 404)
                    db.execute("INSERT INTO reviews(user_id,review_id,started_at) VALUES(?,?,?) ON CONFLICT(user_id,review_id) DO UPDATE SET started_at=excluded.started_at", (uid, qid, now()))
                    return self.respond({"nextUrl": "/pages/practice.html?review=" + qid}, cookie=set_cookie)
                if path == "/api/reports" and method == "GET": return self.respond(self.report(db, uid), cookie=set_cookie)
                if path.startswith("/api/"): return self.fail("API route not found.", 404)
        except (ValueError, json.JSONDecodeError): return self.fail("Request body must be valid JSON.")
        except Exception as exc:
            print(f"API error: {exc}")
            return self.fail("Internal server error.", 500)
        return self.h.serve_frontend(path)

    def practice_questions(self, profile):
        career = profile.get("career") or {}
        specialization = career.get("specializationId")
        if specialization:
            selected_skills = set((career.get("skills") or {}).keys())
            matched = [q for q in questions() if specialization in q.get("specializations", []) and selected_skills.intersection(q.get("skills", []))]
        else:
            role = profile.get("roleId", "")
            role_specs = {"Software Engineer": {"software"}, "Frontend Developer": {"web-development"}, "Backend Developer": {"software", "cloud", "devops"}, "Data Analyst": {"data-science", "business-analytics", "quantitative-analysis"}, "Product Manager": {"product-management", "business-analytics"}}
            labels = {"Problem solving": "problem-solving", "Data structures": "data-structures", "System design": "system-design", "Communication": "communication", "Behavioral interviews": "communication"}
            selected_skills = {labels.get(skill, skill) for skill in profile.get("skillIds", [])}
            allowed_specs = role_specs.get(role, set())
            matched = [q for q in questions() if allowed_specs.intersection(q.get("specializations", [])) and selected_skills.intersection(q.get("skills", []))]
        return matched

    def career_recommendations(self, profile):
        if not profile: return {"matches": []}
        ratings = profile.get("skills", {})
        specialization = profile.get("specializationId")
        labels = {skill["id"]: skill["label"] for skill in CAREER_SKILLS}
        candidates = [path for path in CAREER_PATHS if specialization in path.get("specializations", [])]
        matches = []
        for path in candidates:
            required = path.get("requiredSkills", [])
            values = [ratings.get(skill, 1) for skill in required]
            gaps = [labels.get(skill, skill) for skill in required if ratings.get(skill, 1) < 4]
            tasks = list(path.get("studyTasks", [])) + [f"Strengthen {gap}" for gap in gaps]
            matches.append({"title": path["title"], "matchPercent": clamp(round(sum(values) / max(len(values), 1) * 20)), "description": path.get("description", "Career option based on your selected specialization."), "requiredSkills": [labels.get(skill, skill) for skill in required], "skillGaps": gaps, "studyTasks": tasks[:6], "links": path.get("links", [])})
        matches.sort(key=lambda item: item["matchPercent"], reverse=True)
        return {"matches": matches[:6]}

    def report(self, db, uid):
        return report(db, uid)

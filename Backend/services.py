import json
from datetime import date, datetime, timedelta, timezone
from .data import plan_data, ROLES


def now(): return datetime.now(timezone.utc).isoformat(timespec="seconds")
def clamp(value, low=0, high=100): return max(low, min(high, value))


def user_profile(db, uid):
    row = db.execute("SELECT * FROM profiles WHERE user_id=?", (uid,)).fetchone()
    if not row: return {}
    return {"roleId": row["role_id"], "levelId": row["level_id"], "skillIds": json.loads(row["skill_ids"] or "[]"), "career": json.loads(row["career_data"] or "null")}


def plan_items(db, uid):
    return [dict(r) for r in db.execute("SELECT id,title,description,week,completed FROM plan_items WHERE user_id=? ORDER BY week,id", (uid,))]


def build_plan(db, uid):
    data = plan_data()
    existing = db.execute("SELECT COUNT(*) FROM plan_items WHERE user_id=?", (uid,)).fetchone()[0]
    if not existing:
        for topic in data.get("topics", []):
            for n, session in enumerate(topic.get("sessions", []), 1):
                db.execute("INSERT OR IGNORE INTO plan_items(id,user_id,title,description,week) VALUES(?,?,?,?,?)", (f"{topic['id']}-{n}", uid, session, topic.get("name", "Preparation"), topic.get("week", 1)))
    items = plan_items(db, uid)
    done = sum(bool(i["completed"]) for i in items)
    return {"title": data.get("title", "Your prep plan"), "durationLabel": f"{data.get('durationWeeks', 4)} weeks", "items": [{**i, "completed": bool(i["completed"])} for i in items], "recommendation": "Focus on your next incomplete plan item.", "completed": done, "total": len(items)}


def aggregate(db, uid):
    answers = db.execute("SELECT correct,created_at FROM answers WHERE user_id=? ORDER BY id", (uid,)).fetchall()
    sessions = db.execute("SELECT duration_seconds,created_at FROM focus_sessions WHERE user_id=? AND completed=1 ORDER BY id", (uid,)).fetchall()
    profile = user_profile(db, uid)
    plan = build_plan(db, uid)
    accuracy = round(100 * sum(a["correct"] for a in answers) / len(answers)) if answers else 0
    focus_minutes = sum(s["duration_seconds"] for s in sessions) / 60
    readiness = clamp(round(accuracy * .35 + min(len(sessions), 20) * 2 + plan["completed"] / max(1, plan["total"]) * 35)) if profile.get("roleId") else 0
    return answers, sessions, profile, plan, accuracy, focus_minutes, readiness


def dashboard(db, uid):
    answers, sessions, profile, plan, accuracy, focus_minutes, readiness = aggregate(db, uid)
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    days = []
    for n in range(7):
        day = week_start + timedelta(days=n)
        matching = [s for s in sessions if s["created_at"][:10] == day.isoformat()]
        days.append({"label": day.strftime("%a"), "focusedHours": round(sum(s["duration_seconds"] for s in matching) / 3600, 2), "sessions": len(matching)})
    tasks = []
    for tid, title, category, minutes in [("daily-quiz", "Complete a short practice quiz", "Practice", 10), ("review-plan", "Continue your next prep plan item", "Plan", 20), ("warmup", "Try a warm-up interview prompt", "Interview", 5)]:
        row = db.execute("SELECT completed FROM task_state WHERE user_id=? AND task_id=?", (uid, tid)).fetchone()
        tasks.append({"id": tid, "title": title, "category": category, "minutes": minutes, "completed": bool(row[0]) if row else False})
    return {"hasPreparation": bool(profile.get("roleId")), "user": {"id": uid[:8], "name": "Guest", "role": next((r["label"] for r in ROLES if r["id"] == profile.get("roleId")), ""), "streak": 0}, "readiness": {"score": readiness, "change": 0, "period": "this month", "description": "Complete practice and plan sessions to grow your interview readiness.", "trend": [max(0, readiness-12), max(0, readiness-7), max(0, readiness-3), readiness], "labels": ["W1", "W2", "W3", "W4"], "updatedAt": "today"}, "recommendation": {"topic": "Your next plan item" if plan["total"] else "No focus selected", "score": readiness, "sessions": 3, "minutes": 30, "readinessLift": 5, "href": "pages/plan.html"}, "stats": {"sessions": len(sessions), "sessionsChange": 0, "sessionsCaption": "all time", "accuracy": accuracy, "accuracyChange": 0, "accuracyCaption": f"{len(answers)} questions answered", "focusedHours": round(focus_minutes/60, 1), "hoursChange": 0, "hoursCaption": "all time", "planCompleted": plan["completed"], "planTotal": plan["total"], "planCaption": "sessions complete", "sessionTrend": [d["sessions"] for d in days], "accuracyTrend": [accuracy]*7, "hoursTrend": [round(d["focusedHours"]*100) for d in days]}, "week": {"focusedHours": round(sum(d["focusedHours"] for d in days), 1), "sessions": sum(d["sessions"] for d in days), "streak": 0, "days": days}, "tasks": tasks}

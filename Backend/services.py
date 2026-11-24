import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from .data import plan_data, ROLES, CAREER_SKILLS, CAREER_PATHS, career_catalog

def now(): return datetime.now(timezone.utc).isoformat(timespec="seconds")
def clamp(value, low=0, high=100): return max(low, min(high, value))
def today_utc(): return datetime.now(timezone.utc).date()

def user_profile(db, uid):
    row = db.execute("SELECT * FROM profiles WHERE user_id=?", (uid,)).fetchone()
    if not row: return {}
    return {"roleId": row["role_id"], "levelId": row["level_id"], "skillIds": json.loads(row["skill_ids"] or "[]"), "career": json.loads(row["career_data"] or "null")}

def plan_items(db, uid):
    return [dict(r) for r in db.execute("SELECT id,title,description,week,completed FROM plan_items WHERE user_id=? ORDER BY week,id", (uid,))]

def _career_plan_tasks(profile):
    career = profile.get("career") or {}
    ratings = career.get("skills", {})
    spec_id = career.get("specializationId")
    degree_id = career.get("degreeId")
    catalog = career_catalog()
    spec = next((s for d in catalog.get("degrees", []) if d["id"] == degree_id for s in d.get("specializations", []) if s["id"] == spec_id), None)
    spec_name = spec.get("label", "Career") if spec else "Career"
    labels = {s["id"]: s["label"] for s in catalog.get("skills", [])}
    paths = [p for p in catalog.get("paths", []) if spec_id in p.get("specializations", [])]
    paths.sort(key=lambda p: sum(ratings.get(skill, 1) for skill in p.get("requiredSkills", [])) / max(1, len(p.get("requiredSkills", []))))
    tasks = []
    # First close the user's lowest-rated skill gaps, then work through the
    # specialization's recommended projects and interview practice.
    weak = sorted(ratings, key=lambda skill: (ratings[skill], skill))
    for skill in weak:
        label = labels.get(skill, skill.replace("-", " ").title())
        if ratings[skill] <= 3:
            tasks.extend([(f"Review {label} foundations", f"Build confidence in {label} for {spec_name}."), (f"Practice {label} with a short exercise", f"Apply {label} and record what you learned.")])
    for path in paths:
        tasks.extend((title, path.get("description", f"Practice for {path['title']}.")) for title in path.get("studyTasks", []))
    for skill in weak:
        label = labels.get(skill, skill.replace("-", " ").title())
        tasks.append((f"Build a small {label} project", f"Demonstrate {label} in a portfolio task related to {spec_name}."))
    unique = []
    seen = set()
    for title, description in tasks:
        if title.casefold() not in seen:
            unique.append((title, description))
            seen.add(title.casefold())
        if len(unique) >= 12: break
    while len(unique) < 8:
        n = len(unique) + 1
        unique.append((f"Review {spec_name} practice set {n}", f"Complete and reflect on a focused {spec_name} exercise."))
    return spec_name, unique

def build_plan(db, uid):
    data = plan_data()
    profile = user_profile(db, uid)
    if profile.get("career"):
        spec_name, tasks = _career_plan_tasks(profile)
        fingerprint = json.dumps(profile["career"], sort_keys=True, ensure_ascii=False)
        key = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()[:10]
        prefix = f"u{uid}-{key}-"
        for index, (title, description) in enumerate(tasks, 1):
            week = (index - 1) // 3 + 1
            item_id = f"{prefix}{index}"
            db.execute("INSERT OR IGNORE INTO plan_items(id,user_id,title,description,week) VALUES(?,?,?,?,?)", (item_id, uid, title, description, week))
        items = [item for item in plan_items(db, uid) if item["id"].startswith(prefix)]
        done = sum(bool(item["completed"]) for item in items)
        return {"title": f"{spec_name} Preparation Plan", "durationLabel": "4 weeks", "items": [{**item, "completed": bool(item["completed"])} for item in items], "recommendation": f"Start with {next((i['title'] for i in items if not i['completed']), 'your next review')}; activities are based on your selected skills.", "completed": done, "total": len(items)}

    # General interview plan for users who completed the role/level assessment.
    if isinstance(data.get("weeks"), list):
        for week_data in data["weeks"]:
            week_number = week_data.get("week", 1)
            focus = week_data.get("focus", "Preparation")
            for n, activity in enumerate(week_data.get("activities", []), 1):
                item_id = f"{uid}-general-week-{week_number}-activity-{n}"
                db.execute("INSERT OR IGNORE INTO plan_items(id,user_id,title,description,week) VALUES(?,?,?,?,?)", (item_id, uid, activity, focus, week_number))
        prefix = f"{uid}-general-"
        items = [item for item in plan_items(db, uid) if item["id"].startswith(prefix)]
    else:
        for topic in data.get("topics", []):
            for n, session in enumerate(topic.get("sessions", []), 1):
                item_id = f"{uid}-{topic['id']}-{n}"
                db.execute("INSERT OR IGNORE INTO plan_items(id,user_id,title,description,week) VALUES(?,?,?,?,?)", (item_id, uid, session, topic.get("name", "Preparation"), topic.get("week", 1)))
        items = plan_items(db, uid)
    done = sum(bool(item["completed"]) for item in items)
    return {"title": data.get("title", "Your prep plan"), "durationLabel": f"{data.get('durationWeeks', 4)} weeks", "items": [{**item, "completed": bool(item["completed"])} for item in items], "recommendation": "Focus on your next incomplete plan item.", "completed": done, "total": len(items)}

def aggregate(db, uid):
    answers = db.execute("SELECT correct,created_at FROM answers WHERE user_id=? ORDER BY id", (uid,)).fetchall()
    sessions = db.execute("SELECT duration_seconds,created_at FROM focus_sessions WHERE user_id=? ORDER BY id", (uid,)).fetchall()
    profile = user_profile(db, uid)
    plan = build_plan(db, uid)
    accuracy = round(100 * sum(a["correct"] for a in answers) / len(answers)) if answers else 0
    focus_minutes = sum(s["duration_seconds"] for s in sessions) / 60
    ratings = (profile.get("career") or {}).get("skills", {})
    base = round(sum(ratings.values()) / len(ratings) * 20) if ratings else 0
    readiness = clamp(round(base * .4 + accuracy * .25 + min(len(sessions), 20) * .75 + plan["completed"] / max(1, plan["total"]) * 20)) if (profile.get("roleId") or profile.get("career")) else 0
    return answers, sessions, profile, plan, accuracy, focus_minutes, readiness

def save_readiness_snapshot(db, uid):
    *_, score = aggregate(db, uid)
    day = today_utc().isoformat()
    db.execute("INSERT INTO readiness_snapshots(user_id,snapshot_date,score) VALUES(?,?,?) ON CONFLICT(user_id,snapshot_date) DO UPDATE SET score=excluded.score", (uid, day, score))
    return score

def _daily(rows, today):
    return [(today - timedelta(days=offset), [r for r in rows if r["created_at"][:10] == (today - timedelta(days=offset)).isoformat()]) for offset in range(6, -1, -1)]

def dashboard(db, uid):
    save_readiness_snapshot(db, uid)
    answers, sessions, profile, plan, accuracy, focus_minutes, readiness = aggregate(db, uid)
    today = today_utc()
    daily_focus = _daily(sessions, today)
    daily_answers = _daily(answers, today)
    days = [{"label": day.strftime("%a"), "focusedHours": round(sum(s["duration_seconds"] for s in focus_group) / 3600, 2), "sessions": len(focus_group), "answers": len(answer_group)} for (day, focus_group), (_, answer_group) in zip(daily_focus, daily_answers)]
    accuracy_trend = [round(100 * sum(a["correct"] for a in group) / len(group)) if group else 0 for _, group in _daily(answers, today)]
    snapshots = db.execute("SELECT snapshot_date,score FROM readiness_snapshots WHERE user_id=? ORDER BY snapshot_date", (uid,)).fetchall()
    week_starts = [today - timedelta(days=today.weekday() + 7 * offset) for offset in (3, 2, 1, 0)]
    trend = []
    for start in week_starts:
        end = start + timedelta(days=7)
        values = [s["score"] for s in snapshots if start.isoformat() <= s["snapshot_date"] < end.isoformat()]
        trend.append(round(sum(values) / len(values)) if values else 0)
    tasks = []
    for tid, title, category, minutes in [("daily-quiz", "Complete a short practice quiz", "Practice", 10), ("review-plan", "Continue your next prep plan item", "Plan", 20), ("warmup", "Try a warm-up interview prompt", "Interview", 5)]:
        row = db.execute("SELECT completed FROM task_state WHERE user_id=? AND task_id=?", (uid, tid)).fetchone()
        tasks.append({"id": tid, "title": title, "category": category, "minutes": minutes, "completed": bool(row[0]) if row else False})
    role = next((r["label"] for r in ROLES if r["id"] == profile.get("roleId")), "")
    if not role and profile.get("career"):
        spec = profile["career"].get("specializationId", "")
        role = spec.replace("-", " ").title()
    account = db.execute("SELECT name FROM users WHERE id=?", (uid,)).fetchone()
    display_name = account["name"] if account and account["name"] else "Guest"
    return {"hasPreparation": bool(profile.get("roleId") or profile.get("career")), "user": {"id": uid[:8], "name": display_name, "role": role, "streak": 0}, "readiness": {"score": readiness, "change": 0, "period": "this month", "description": "Complete practice and plan sessions to grow your interview readiness.", "trend": trend, "labels": ["W1", "W2", "W3", "W4"], "updatedAt": "today"}, "recommendation": {"topic": "Your next plan item" if plan["total"] else "No focus selected", "score": readiness, "sessions": 3, "minutes": 30, "readinessLift": 5, "href": "pages/plan.html"}, "stats": {"sessions": len(sessions), "sessionsChange": 0, "sessionsCaption": "all time", "accuracy": accuracy, "accuracyChange": 0, "accuracyCaption": f"{len(answers)} questions answered", "focusedHours": round(focus_minutes/60, 1), "hoursChange": 0, "hoursCaption": "all time", "planCompleted": plan["completed"], "planTotal": plan["total"], "planCaption": "sessions complete", "sessionTrend": [d["sessions"] for d in days], "accuracyTrend": accuracy_trend, "hoursTrend": [round(d["focusedHours"]*100) for d in days]}, "week": {"focusedHours": round(sum(d["focusedHours"] for d in days), 1), "sessions": sum(d["sessions"] for d in days), "answers": sum(d["answers"] for d in days), "streak": 0, "days": days}, "tasks": tasks}

def report(db, uid):
    answers, sessions, profile, plan, accuracy, focus_minutes, readiness = aggregate(db, uid)
    labels = {s["id"]: s["label"] for s in CAREER_SKILLS}
    ratings = (profile.get("career") or {}).get("skills", {})
    selected = [{"id": key, "name": labels.get(key, key.replace("-", " ").title()), "score": round(value * 20)} for key, value in ratings.items()]
    selected_ids = set(ratings)
    selected.extend({"id": skill, "name": skill.replace("-", " ").title(), "score": None} for skill in profile.get("skillIds", []) if skill not in selected_ids)
    wins = []
    if answers: wins.append({"icon": "✓", "title": "Practice answers recorded", "description": f"You have answered {len(answers)} questions with {accuracy}% accuracy."})
    if plan["completed"]: wins.append({"icon": "✧", "title": "Plan progress", "description": f"Completed {plan['completed']} prep plan items."})
    if sessions: wins.append({"icon": "◷", "title": "Focused practice", "description": f"Logged {round(focus_minutes/60,1)} focused hours."})
    if ratings: wins.append({"icon": "✦", "title": "Career profile saved", "description": f"Your profile includes {len(ratings)} self-rated skills."})
    today = today_utc()
    week_start = today - timedelta(days=today.weekday())
    focused_days = len({s["created_at"][:10] for s in sessions if week_start.isoformat() <= s["created_at"][:10] <= today.isoformat()})
    recent = db.execute("SELECT score FROM readiness_snapshots WHERE user_id=? AND snapshot_date<=? ORDER BY snapshot_date DESC LIMIT 2", (uid, today.isoformat())).fetchall()
    change = recent[0]["score"] - recent[1]["score"] if len(recent) > 1 else 0
    dates = sorted({a["created_at"][:10] for a in answers} | {s["created_at"][:10] for s in sessions})
    best = streak = 0
    previous = None
    for value in dates:
        day = date.fromisoformat(value)
        streak = streak + 1 if previous and day == previous + timedelta(days=1) else 1
        best = max(best, streak)
        previous = day
    return {"metrics": {"readinessScore": readiness, "readinessChange": change, "readinessPeriod": "points in 30 days", "practiceSessions": len(sessions), "sessionsChange": 0, "sessionsPeriod": "this month", "focusedHours": round(focus_minutes/60, 1), "focusedDays": focused_days, "streakBest": best, "streakCaption": "Personal best"}, "selectedSkills": selected, "recentWins": wins, "insight": "Small, regular practice sessions help build confidence over time." if answers or sessions else "Start a skill assessment and complete a practice session to see personalized insights."}

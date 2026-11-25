
from flask import Flask, render_template, request, jsonify, session
from pathlib import Path
import json

from recommendation import recommend_careers
from scheduler import create_study_schedule


app = Flask(__name__)
app.secret_key = "updraft-development-key-change-before-deployment"

# --------------------------------------------------
# 1. LOAD CAREER DATA
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
CAREER_DATA_FILE = BASE_DIR / "career_data.json"
PRACTICE_DATA_FILE = BASE_DIR / "practice_questions.json"


SKILL_NAMES = [
    "programming",
    "math_statistics",
    "data_analysis",
    "problem_solving",
    "machine_learning",
    "cybersecurity_networking",
    "communication"
]


def load_career_data():
    """Load career information from career_data.json."""

    with open(CAREER_DATA_FILE, "r", encoding="utf-8") as file:
        return json.load(file)

def load_practice_data():
    with open(PRACTICE_DATA_FILE, "r", encoding="utf-8") as file:
        return json.load(file)
career_data = load_career_data()
practice_data = load_practice_data()

@app.route("/api/career/options", methods=["GET"])
def career_options():
    degrees = {}

    for career in career_data.get("careers", []):
        for degree in career.get("eligible_degrees", []):
            if degree not in degrees:
                degrees[degree] = set()

            degrees[degree].update(career.get("specializations", []))

    degree_options = []

    for degree, specializations in degrees.items():
        degree_options.append({
            "id": degree,
            "label": degree,
            "specializations": [
                {"id": item, "label": item}
                for item in sorted(specializations)
            ]
        })

    skills = [
        {"id": "programming", "label": "Programming"},
        {"id": "math_statistics", "label": "Mathematics and Statistics"},
        {"id": "data_analysis", "label": "Data Analysis"},
        {"id": "problem_solving", "label": "Problem Solving"},
        {"id": "machine_learning", "label": "Machine Learning"},
        {"id": "cybersecurity_networking", "label": "Cybersecurity and Networking"},
        {"id": "communication", "label": "Communication"}
    ]

    return jsonify({
        "degrees": degree_options,
        "skills": skills
    })



# --------------------------------------------------
# 2. READ AND VALIDATE STUDENT INFORMATION
# --------------------------------------------------

def get_student_data(data):
    """
    Extract student information from either
    an HTML form or a JSON request.
    """

    degree = data.get("degree", "")
    specialization = data.get("specialization", "")
    year = data.get("year", "")

    if not degree or not specialization or not year:
        raise ValueError(
            "Please provide degree, specialization, and year."
        )

    try:
        year = int(year)
    except (TypeError, ValueError):
        raise ValueError("Year must be a valid number.")

    if year < 1:
        raise ValueError("Year must be at least 1.")

    # Read the student's skill ratings.
    skills = data.get("skills", {})

    if not isinstance(skills, dict):
        skills = {}

    # HTML forms may send skills as separate fields.
    for skill in SKILL_NAMES:
        if skill in data:
            skills[skill] = data.get(skill)

    validated_skills = {}

    for skill in SKILL_NAMES:
        value = skills.get(skill, 1)

        try:
            value = int(value)
        except (TypeError, ValueError):
            raise ValueError(
                f"Invalid rating for {skill}."
            )

        if value < 1 or value > 5:
            raise ValueError(
                f"{skill} rating must be between 1 and 5."
            )

        validated_skills[skill] = value

    return {
        "degree": degree.strip(),
        "specialization": specialization.strip(),
        "year": year,
        "skills": validated_skills
    }


# --------------------------------------------------
# 3. RECOMMEND CAREERS AND CREATE STUDY SCHEDULES
# --------------------------------------------------


# --------------------------------------------------
# 3. RECOMMEND CAREERS AND CREATE STUDY SCHEDULES
# --------------------------------------------------

def generate_recommendations(student):
    """
    Generate career recommendations and study schedules.
    """
    recommendations = recommend_careers(student, career_data)

    for career in recommendations:
        skill_gaps = career.get("skill_gaps", [])

        career["study_schedule"] = create_study_schedule(
            skill_gaps
        )

    return recommendations


# --------------------------------------------------
# 3A. BUILD STUDY PLAN ITEMS
# --------------------------------------------------

def build_plan_items(recommendations):
    """
    Convert career recommendations into study plan tasks.
    """

    if not recommendations:
        return []

    best_match = recommendations[0]
    tasks = best_match.get("study_schedule", [])

    items = []

    for index, task in enumerate(tasks, start=1):
        skill = task.get("skill", "General skill")
        skill_name = skill.replace("_", " ").title()

        items.append({
            "id": skill,
            "title": f"Improve {skill_name}",
            "description": (
                f"Estimated {task.get('burst_time', 0)} study hours. "
                f"Priority: {task.get('priority', 0)}."
            ),
            "week": ((index - 1) // 2) + 1,
            "completed": False
        })

    return items


# --------------------------------------------------
# 4. HOME PAGE
# --------------------------------------------------
# --------------------------------------------------
# 4A. FRONTEND PAGE ROUTES
# --------------------------------------------------

# --------------------------------------------------
# 4A. FRONTEND PAGE ROUTES
# --------------------------------------------------

@app.route("/pages/assessment")
@app.route("/pages/assessment.html")
def assessment_page():
    return render_template("pages/assessment.html")


@app.route("/pages/plan")
@app.route("/pages/plan.html")
def plan_page():
    return render_template("pages/plan.html")


@app.route("/pages/practice")
@app.route("/pages/practice.html")
def practice_page():
    return render_template("pages/practice.html")


@app.route("/pages/reports")
@app.route("/pages/reports.html")
def reports_page():
    return render_template("pages/reports.html")

@app.route("/")
def home():
    return render_template("index.html")


# --------------------------------------------------
# 5. RESULTS PAGE
# --------------------------------------------------
@app.route("/results", methods=["GET", "POST"])
def results():

    if request.method == "GET":
        return render_template("results.html")

    try:
        student = get_student_data(request.form)
        recommendations = generate_recommendations(student)

        return render_template(
            "results.html",
            student=student,
            recommendations=recommendations
        )

    except ValueError as error:
        return render_template(
            "results.html",
            student=request.form,
            recommendations=[],
            error=str(error)
        ), 400


    

@app.route("/api/career/assessment", methods=["POST"])
def submit_career_assessment():
    try:
        data = request.get_json(silent=True) or {}

        # Convert frontend field names into Python field names.
        student_data = {
            "degree": data.get("degreeId", ""),
            "specialization": data.get("specializationId", ""),
            "year": data.get("studyYear", ""),
            "skills": data.get("skills", {})
        }

        student = get_student_data(student_data)
        recommendations = generate_recommendations(student)

        # Remember the results for this browser session.
        session["career_student"] = student
        session["career_recommendations"] = recommendations

        return jsonify({
            "success": True,
            "message": "Assessment completed successfully."
        })

    except ValueError as error:
        return jsonify({
            "success": False,
            "error": str(error)
        }), 400

@app.route("/api/career/recommendations", methods=["GET"])
def get_career_recommendations():
    recommendations = session.get("career_recommendations")

    if recommendations is None:
        return jsonify({
            "success": False,
            "error": "Please complete your assessment first.",
            "recommendations": []
        }), 404

    return jsonify({
        "success": True,
        "student": session.get("career_student", {}),
        "recommendations": recommendations
    })


# --------------------------------------------------
# 6. CAREER RECOMMENDATION API
# --------------------------------------------------

@app.route(
    "/api/career/recommendations",
    methods=["POST"]
)
def career_recommendation_api():

    try:
        data = request.get_json(silent=True) or {}

        student = get_student_data(data)

        recommendations = generate_recommendations(student)

        return jsonify({
            "success": True,
            "student": student,
            "recommendations": recommendations
        })

    except ValueError as error:
        return jsonify({
            "success": False,
            "error": str(error),
            "recommendations": []
        }), 400


# --------------------------------------------------
# 7. TEST WHETHER THE SERVER IS RUNNING
# --------------------------------------------------
# GET: Load the student's study plan
@app.route("/api/plan", methods=["GET"])
def get_study_plan():

    recommendations = session.get("career_recommendations", [])

    # Build the plan only once, so completed tasks are preserved
    if "plan_items" not in session:
        session["plan_items"] = build_plan_items(recommendations)

    items = session["plan_items"]

    recommendation = ""
    if recommendations:
        recommendation = (
            f"Focus on improving skills for "
            f"{recommendations[0].get('role', 'your selected career')}."
        )

    return jsonify({
        "title": "Your Personalized Study Plan",
        "durationLabel": f"{len(items)} study tasks",
        "items": items,
        "recommendation": recommendation
    })


# PATCH: Update a task's completion status
@app.route("/api/plan/items/<item_id>", methods=["PATCH"])
def update_plan_item(item_id):

    data = request.get_json(silent=True) or {}
    completed = data.get("completed")

    if not isinstance(completed, bool):
        return jsonify({
            "success": False,
            "error": "Completed must be true or false."
        }), 400

    items = session.get("plan_items", [])

    for item in items:
        if str(item["id"]) == item_id:
            item["completed"] = completed
            session["plan_items"] = items

            return jsonify({
                "success": True,
                "item": item
            })

    return jsonify({
        "success": False,
        "error": "Study plan item not found."
    }), 404


# POST: Schedule editing endpoint
@app.route("/api/plan/schedule", methods=["POST"])
def edit_study_schedule():

    return jsonify({
        "success": True,
        "message": "Schedule endpoint is working."
    })

# --------------------------------------------------
# REPORTS MODULE - REPORT API
# --------------------------------------------------

@app.route("/api/reports", methods=["GET"])
def get_reports():

    # Retrieve assessment information
    student = session.get("career_student", {})
    skills = student.get("skills", {})

    # Convert skill ratings into percentages
    selected_skills = []

    for skill_name, rating in skills.items():
        score = rating * 20

        selected_skills.append({
            "id": skill_name.lower().replace(" ", "-"),
            "name": skill_name,
            "score": score
        })

    # Calculate estimated readiness
    if selected_skills:
        readiness_score = round(
            sum(skill["score"] for skill in selected_skills)
            / len(selected_skills)
        )
    else:
        readiness_score = 0

    # Retrieve completed focus sessions
    focus_sessions = session.get("focus_sessions", [])

    practice_sessions = len(focus_sessions)

    total_seconds = sum(
        item.get("durationSeconds", 0)
        for item in focus_sessions
    )

    focused_hours = round(total_seconds / 3600, 1)

    # Build report metrics
    metrics = {
        "readinessScore": readiness_score,
        "readinessChange": 0,
        "readinessPeriod": "estimated skill rating",

        "practiceSessions": practice_sessions,
        "sessionsChange": 0,
        "sessionsPeriod": "completed focus sessions",

        "focusedHours": focused_hours,
        "focusedDays": 0,

        "streakBest": 0,
        "streakCaption": "Daily activity tracking not available yet"
    }

    # Build report insight
    if not student:
        insight = "Complete your career assessment to see your skill progress."
    elif not focus_sessions:
        insight = "Your assessment is complete. Start focus sessions to build your practice history."
    else:
        insight = "Keep practising consistently to improve your skills."

    return jsonify({
        "metrics": metrics,
        "selectedSkills": selected_skills,
        "recentWins": [],
        "insight": insight
    })


@app.route("/api/health")
def health_check():
    return jsonify({
        "status": "running",
        "message": "Updraft Flask backend is working!"
    })


# --------------------------------------------------
# PRACTICE MODULE - QUIZ APIs
# --------------------------------------------------

# GET: Send quiz questions to the frontend
@app.route("/api/practice/questions", methods=["GET"])
def get_practice_questions():
    questions = practice_data.get("questions", [])

    public_questions = []

    for question in questions:
        public_questions.append({
            "id": question["id"],
            "prompt": question["prompt"],
            "options": question["options"]
        })

    return jsonify({
        "questions": public_questions
    })


# POST: Check the selected quiz answer
@app.route("/api/practice/answers", methods=["POST"])
def check_practice_answer():
    data = request.get_json(silent=True) or {}

    question_id = data.get("questionId")
    option_id = data.get("optionId")

    if not question_id or not option_id:
        return jsonify({
            "success": False,
            "error": "Question ID and option ID are required."
        }), 400

    questions = practice_data.get("questions", [])

    question = next(
        (q for q in questions if q["id"] == question_id),
        None
    )

    if question is None:
        return jsonify({
            "success": False,
            "error": "Question not found."
        }), 404

    valid_options = [
        option["id"] for option in question["options"]
    ]

    if option_id not in valid_options:
        return jsonify({
            "success": False,
            "error": "Invalid answer option."
        }), 400

    correct = option_id == question["correct_option_id"]

    return jsonify({
        "correct": correct,
        "explanation": question.get("explanation", "")
    })

# GET: Send daily warm-up prompts
@app.route("/api/practice/warmups", methods=["GET"])
def get_practice_warmups():
    prompts = practice_data.get("warmups", [])

    return jsonify({
        "prompts": prompts
    })

# POST: Save a completed focus session
@app.route("/api/practice/focus-sessions", methods=["POST"])
def save_focus_session():
    data = request.get_json(silent=True) or {}

    duration = data.get("durationSeconds")
    prompt_id = data.get("promptId")
    completed = data.get("completed")

    if (
        not isinstance(duration, int)
        or isinstance(duration, bool)
        or duration <= 0
        or not isinstance(completed, bool)
        or completed is not True
    ):
        return jsonify({
            "success": False,
            "error": "Invalid focus session details."
        }), 400

    prompts = practice_data.get("warmups", [])

    if not any(prompt["id"] == prompt_id for prompt in prompts):
        return jsonify({
            "success": False,
            "error": "Invalid warm-up prompt."
        }), 400

    sessions = session.get("focus_sessions", [])

    sessions.append({
        "durationSeconds": duration,
        "promptId": prompt_id,
        "completed": True
    })

    session["focus_sessions"] = sessions

    return jsonify({
        "success": True,
        "message": "Focus session completed successfully."
    })
# GET: Send review items to the frontend
@app.route("/api/practice/reviews", methods=["GET"])
def get_practice_reviews():
    items = practice_data.get("reviews", [])

    return jsonify({
        "items": items
    })


# POST: Start a review session
@app.route("/api/practice/reviews/<review_id>/start", methods=["POST"])
def start_practice_review(review_id):
    reviews = practice_data.get("reviews", [])

    review = next(
        (item for item in reviews if item["id"] == review_id),
        None
    )

    if review is None:
        return jsonify({
            "success": False,
            "error": "Review item not found."
        }), 404

    return jsonify({
        "success": True,
        "message": f"Review session started: {review['title']}"
    })
# GET: Send dashboard information to the frontend
@app.route("/api/dashboard", methods=["GET"])
def get_dashboard():

    # Get existing session data
    student = session.get("career_student", {})
    recommendations = session.get("career_recommendations", [])
    focus_sessions = session.get("focus_sessions", [])
    plan_items = session.get("plan_items", [])

    # Calculate readiness score from skill ratings
    skills = student.get("skills", {})

    if skills:
        readiness_score = round(
            sum(skills.values()) * 20 / len(skills)
        )
    else:
        readiness_score = 0

    # Calculate focus statistics
    total_seconds = sum(
        item.get("durationSeconds", 0)
        for item in focus_sessions
    )

    focused_hours = round(total_seconds / 3600, 1)
    practice_sessions = len(focus_sessions)

    # Calculate study plan progress
    plan_total = len(plan_items)
    plan_completed = sum(
        1 for item in plan_items if item.get("completed")
    )

    # Get recommended career
    recommendation = recommendations[0] if recommendations else {}

    # Prepare dashboard response
    return jsonify({
        "hasPreparation": bool(student),

        "user": {
            "name": "Student",
            "role": student.get("specialization", "Learner"),
            "id": "Student",
            "streak": 0
        },

        "readiness": {
            "score": readiness_score,
            "change": 0,
            "period": "Current assessment",
            "description": "Based on your self-rated skills.",
            "trend": [],
            "labels": [],
            "updatedAt": ""
        },

        "recommendation": {
            "topic": recommendation.get("role", "No recommendation yet"),
            "score": readiness_score,
            "sessions": practice_sessions,
            "minutes": round(total_seconds / 60),
            "readinessLift": 0,
            "href": "/pages/plan"
        },

        "stats": {
            "sessions": practice_sessions,
            "sessionsChange": 0,
            "sessionsCaption": "Completed focus sessions",

            "accuracy": 0,
            "accuracyChange": 0,
            "accuracyCaption": "Quiz tracking not available yet",

            "focusedHours": focused_hours,
            "hoursChange": 0,
            "hoursCaption": "Total focused time",

            "planCompleted": plan_completed,
            "planTotal": plan_total,
            "planCaption": "Study tasks completed",

            "sessionTrend": [],
            "accuracyTrend": [],
            "hoursTrend": []
        },

        "week": {
            "focusedHours": focused_hours,
            "sessions": practice_sessions,
            "streak": 0,
            "days": []
        },

        "tasks": [
            {
                "id": item["id"],
                "title": item["title"],
                "category": "Study Plan",
                "minutes": 0,
                "completed": item.get("completed", False)
            }
            for item in plan_items
        ]
    })



# --------------------------------------------------
# 8. START FLASK
# --------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)

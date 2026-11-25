
def _normalise(text):
    """Make text comparisons ignore letter case and extra spaces."""
    return " ".join(text.lower().split())


def _degree_matches(student_degree, eligible_degrees):
    """Check whether the student's degree is listed for a career."""
    student_degree = _normalise(student_degree)

    return any(
        _normalise(degree) in student_degree
        or student_degree in _normalise(degree)
        for degree in eligible_degrees
    )


def _specialization_matches(student_specialization, specializations):
    """Check whether the student's specialization is listed for a career."""
    student_specialization = _normalise(student_specialization)

    return any(
        _normalise(item) in student_specialization
        or student_specialization in _normalise(item)
        for item in specializations
    )


def compare_skills(student_skills, required_skills):
    """
    Compare student skill ratings with career requirements.

    Returns a list of skills that need improvement, largest gap first.
    """
    gaps = []

    for skill, required_level in required_skills.items():
        current_level = student_skills.get(skill, 1)
        gap = max(0, required_level - current_level)

        if gap > 0:
            if gap >= 3:
                label = "high"
            elif gap == 2:
                label = "medium"
            else:
                label = "small"

            gaps.append({
                "skill": skill,
                "current_level": current_level,
                "required_level": required_level,
                "gap": gap,
                "label": label
            })

    return sorted(gaps, key=lambda item: item["gap"], reverse=True)


def recommend_careers(student, career_data):
    """
    Return careers that match the student's degree, specialization, and year.
    """
    results = []

    for career in career_data.get("careers", []):
        degrees = career.get("eligible_degrees", [])
        specializations = career.get("specializations", [])
        minimum_year = career.get("minimum_year", 1)

        if not _degree_matches(student["degree"], degrees):
            continue

        if not _specialization_matches(
            student["specialization"], specializations
        ):
            continue

        if student["year"] < minimum_year:
            continue

        gaps = compare_skills(
            student.get("skills", {}),
            career.get("skills", {})
        )

        results.append({
            "role": career["role"],
            "description": career.get("description", ""),
            "opportunity_link": career.get("opportunity_link", ""),
            "higher_study": career.get("higher_study", ""),
            "source": career.get("source", ""),
            "checked_on": career.get("checked_on", ""),
            "skill_gaps": gaps
        })

    return results

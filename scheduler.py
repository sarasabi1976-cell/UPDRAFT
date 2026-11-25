
def create_study_schedule(skill_gaps):
    """
    Schedule study tasks from largest skill gap to smallest.

    Each gap should contain:
    {
        "skill": "programming",
        "gap": 2
    }

    Estimated burst time is 2 study hours per gap point.
    """
    tasks = []

    for item in skill_gaps:
        gap = item["gap"]

        tasks.append({
            "skill": item["skill"],
            "priority": gap,
            "burst_time": gap * 2
        })

    # Larger gap means higher priority.
    # If two gaps are equal, keep their original order.
    tasks.sort(key=lambda task: task["priority"], reverse=True)

    elapsed_hours = 0

    for task in tasks:
        task["waiting_time"] = elapsed_hours
        elapsed_hours += task["burst_time"]
        task["turnaround_time"] = elapsed_hours

    return tasks


# progress.py

import json
from datetime import datetime


# Create a progress tracker for a roadmap
def create_progress(roadmap, duration_weeks):
    if not isinstance(duration_weeks, int) or not 1 <= duration_weeks <= 52:
        raise ValueError("Duration must be between 1 and 52 weeks.")

    if not isinstance(roadmap, str) or not roadmap.strip():
        raise ValueError("A valid roadmap is required.")

    # Create one progress entry for every week
    weekly_progress = []

    for week in range(1, duration_weeks + 1):
        weekly_progress.append({
            "week": week,
            "completed": False,
            "notes": "",
        })

    return {
        "roadmap": roadmap,
        "duration_weeks": duration_weeks,
        "weekly_progress": weekly_progress,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }


# Mark a weekly milestone as completed or incomplete
def update_week_progress(progress, week_number, completed, notes=""):
    if not isinstance(week_number, int):
        raise ValueError("Week number must be an integer.")

    if not 1 <= week_number <= progress["duration_weeks"]:
        raise ValueError("Week number is outside the roadmap duration.")

    for item in progress["weekly_progress"]:
        if item["week"] == week_number:
            item["completed"] = bool(completed)
            item["notes"] = str(notes)
            progress["updated_at"] = datetime.now().isoformat(
                timespec="seconds"
            )
            return progress

    raise ValueError("The requested week was not found.")


# Calculate completion statistics
def get_progress_summary(progress):
    weekly_progress = progress["weekly_progress"]
    total_weeks = len(weekly_progress)

    completed_weeks = sum(
        1 for item in weekly_progress if item["completed"]
    )

    percentage = (
        round(completed_weeks / total_weeks * 100, 1)
        if total_weeks
        else 0
    )

    return {
        "total_weeks": total_weeks,
        "completed_weeks": completed_weeks,
        "remaining_weeks": total_weeks - completed_weeks,
        "completion_percentage": percentage,
    }


# Export progress as JSON text
def export_progress(progress):
    return json.dumps(progress, indent=4, ensure_ascii=False)


# Import progress from JSON text
def import_progress(json_text):
    try:
        data = json.loads(json_text)
    except (json.JSONDecodeError, TypeError) as error:
        raise ValueError("The progress file is not valid JSON.") from error

    # Validate the basic structure before accepting imported data
    if not isinstance(data, dict):
        raise ValueError("The imported progress must be a JSON object.")

    duration = data.get("duration_weeks")
    weekly_progress = data.get("weekly_progress")
    roadmap = data.get("roadmap")

    if (
        not isinstance(duration, int)
        or isinstance(duration, bool)
        or not 1 <= duration <= 52
    ):
        raise ValueError("The imported duration must be between 1 and 52.")

    if not isinstance(roadmap, str) or not roadmap.strip():
        raise ValueError("The imported roadmap is missing or invalid.")

    if not isinstance(weekly_progress, list):
        raise ValueError("The imported weekly progress is invalid.")

    if len(weekly_progress) != duration:
        raise ValueError(
            "The number of progress entries does not match the duration."
        )

    seen_weeks = set()

    for item in weekly_progress:
        if not isinstance(item, dict):
            raise ValueError("A weekly progress entry is invalid.")

        week = item.get("week")

        if (
            not isinstance(week, int)
            or isinstance(week, bool)
            or not 1 <= week <= duration
            or week in seen_weeks
        ):
            raise ValueError("A week number is invalid or duplicated.")

        if not isinstance(item.get("completed"), bool):
            raise ValueError("A completion status must be true or false.")

        if not isinstance(item.get("notes", ""), str):
            raise ValueError("Weekly notes must be text.")

        seen_weeks.add(week)

    if seen_weeks != set(range(1, duration + 1)):
        raise ValueError("One or more weeks are missing.")

    # Normalize optional timestamp fields
    data.setdefault("created_at", datetime.now().isoformat(timespec="seconds"))
    data.setdefault("updated_at", datetime.now().isoformat(timespec="seconds"))

    return data

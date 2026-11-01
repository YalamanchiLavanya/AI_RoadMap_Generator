"""Tasks, completion tracking, progress export/import, and plan state changes.

The progress tracker is built FROM the roadmap: every activity and weekly milestone
becomes a task. When a revised roadmap is applied, tasks are rebuilt from the new
plan and completion is carried over for tasks that are still in it.

The state functions take any mutable mapping, so they work on ``st.session_state``
and on a plain ``dict`` in tests.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import MutableMapping

from config import MAX_WEEKS, LearnerProfile
from roadmap_engine import (
    RevisionResult,
    normalize_plan,
    plan_to_markdown,
    validate_plan,
)

EXPORT_APP = "ai-learning-roadmap-generator"
EXPORT_VERSION = 1
MAX_IMPORT_BYTES = 2_000_000
MAX_CUSTOM_TASK_LENGTH = 200


class ProgressImportError(ValueError):
    """The progress file cannot be used. The message is safe to show."""


# ==========================================================================
# Tasks
# ==========================================================================
def _key(week, name: str) -> tuple:
    return (week, " ".join(str(name).casefold().split()))


def tasks_from_plan(plan: dict) -> list[dict]:
    """One task per activity plus one per weekly milestone (all not done)."""
    tasks: list[dict] = []
    for week in plan.get("weeks", []):
        number = week["week"]
        for index, activity in enumerate(week.get("activities", []), start=1):
            tasks.append(
                {
                    "id": f"w{number}-{index}",
                    "week": number,
                    "name": activity["task"],
                    "hours": float(activity["hours"]),
                    "type": activity["type"],
                    "done": False,
                    "source": "plan",
                }
            )
        tasks.append(
            {
                "id": f"w{number}-m",
                "week": number,
                "name": f"Milestone: {week.get('milestone', '')}",
                "hours": 0.0,
                "type": "milestone",
                "done": False,
                "source": "plan",
            }
        )
    return tasks


def merge_tasks(old_tasks: list[dict], new_plan_tasks: list[dict]) -> list[dict]:
    """New plan tasks keep their 'done' flag when the same task still exists.

    Tasks the learner added themselves are always kept.
    """
    done_before = {
        _key(task.get("week"), task["name"]): bool(task.get("done"))
        for task in old_tasks
        if task.get("source") == "plan"
    }
    merged = []
    for task in new_plan_tasks:
        task = dict(task)
        task["done"] = done_before.get(_key(task["week"], task["name"]), False)
        merged.append(task)
    merged.extend(dict(task) for task in old_tasks if task.get("source") == "custom")
    return merged


def add_custom_task(tasks: list[dict], name: str, week: int | None = None) -> tuple[bool, str]:
    """Append a learner-written task. Returns (added, message)."""
    clean = " ".join((name or "").split())
    if not clean:
        return False, "Enter a task name."
    if len(clean) > MAX_CUSTOM_TASK_LENGTH:
        return False, f"Keep the task under {MAX_CUSTOM_TASK_LENGTH} characters."
    if any(_key(task.get("week"), task["name"]) == _key(week, clean) for task in tasks):
        return False, "This task already exists."
    used = [int(t["id"][1:]) for t in tasks if str(t.get("id", "")).startswith("c") and t["id"][1:].isdigit()]
    tasks.append(
        {
            "id": f"c{(max(used) + 1) if used else 1}",
            "week": week,
            "name": clean,
            "hours": 0.0,
            "type": "custom",
            "done": False,
            "source": "custom",
        }
    )
    return True, "Task added."


def progress_stats(tasks: list[dict]) -> dict:
    total = len(tasks)
    done = sum(1 for task in tasks if task.get("done"))
    per_week: dict[int, dict] = {}
    for task in tasks:
        week = task.get("week")
        if week is None:
            continue
        bucket = per_week.setdefault(week, {"done": 0, "total": 0})
        bucket["total"] += 1
        bucket["done"] += 1 if task.get("done") else 0
    current = next((w for w in sorted(per_week) if per_week[w]["done"] < per_week[w]["total"]), None)
    hours_total = sum(float(t.get("hours") or 0) for t in tasks if t.get("source") == "plan")
    hours_done = sum(float(t.get("hours") or 0) for t in tasks if t.get("source") == "plan" and t.get("done"))
    return {
        "total": total,
        "done": done,
        "percent": round(done / total * 100) if total else 0,
        "per_week": per_week,
        "current_week": current,
        "hours_done": round(hours_done, 2),
        "hours_total": round(hours_total, 2),
    }


def progress_summary_text(tasks: list[dict], max_items: int = 15) -> str:
    """Plain-text progress for the coach and for revision prompts.

    There are no dates in the tracker, so this reports completion only - it does
    not claim the learner is "behind schedule".
    """
    if not tasks:
        return ""
    stats = progress_stats(tasks)
    lines = [f"{stats['done']} of {stats['total']} tasks done ({stats['percent']}%)."]
    if stats["current_week"] is not None:
        lines.append(f"First week with unfinished tasks: week {stats['current_week']}.")
    else:
        lines.append("All tasks are done.")
    for week in sorted(stats["per_week"]):
        bucket = stats["per_week"][week]
        lines.append(f"Week {week}: {bucket['done']}/{bucket['total']} done")
    completed = [t["name"] for t in tasks if t.get("done")]
    if completed:
        lines.append("Completed tasks: " + "; ".join(completed[:max_items]) + ("; ..." if len(completed) > max_items else ""))
    open_tasks = [f"(week {t.get('week')}) {t['name']}" for t in tasks if not t.get("done")]
    if open_tasks:
        lines.append("Open tasks: " + "; ".join(open_tasks[:max_items]) + ("; ..." if len(open_tasks) > max_items else ""))
    return "\n".join(lines)


# ==========================================================================
# Export / import
# ==========================================================================
def export_progress(state: MutableMapping) -> str:
    """Serialise plan, profile, and tasks so a learner can resume later."""
    index = state.get("pdf_index")
    payload = {
        "app": EXPORT_APP,
        "schema_version": EXPORT_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "plan_version": state.get("plan_version", 1),
        "profile": state.get("plan_profile") or {},
        "plan": state.get("roadmap_plan") or {},
        "tasks": state.get("tasks") or [],
        "pdf_filename": index.filename if index else (state.get("roadmap_plan") or {}).get("reference", {}).get("filename"),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def import_progress(text: str | bytes) -> dict:
    """Parse and validate a saved progress file. Raises ProgressImportError."""
    raw = text.decode("utf-8", errors="replace") if isinstance(text, bytes) else text
    if len(raw.encode("utf-8")) > MAX_IMPORT_BYTES:
        raise ProgressImportError("The progress file is too large.")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ProgressImportError("That file is not valid JSON.") from exc
    if not isinstance(data, dict) or data.get("app") != EXPORT_APP:
        raise ProgressImportError("That file was not exported by this app.")
    if data.get("schema_version") != EXPORT_VERSION:
        raise ProgressImportError(f"Unsupported progress file version: {data.get('schema_version')!r}.")

    saved_plan = data.get("plan")
    if not isinstance(saved_plan, dict):
        raise ProgressImportError("The file contains no roadmap.")
    plan, _ = normalize_plan(saved_plan)
    constraints = plan.get("constraints") or {}
    hours, weeks = constraints.get("hours_per_week"), constraints.get("duration_weeks")
    plan["constraints"] = {"hours_per_week": hours, "duration_weeks": weeks}
    plan.pop("change_summary", None)
    reference = saved_plan.get("reference")
    if isinstance(reference, dict) and isinstance(reference.get("filename"), str):
        pages = [p for p in reference.get("pages", []) if isinstance(p, int) and p > 0]
        plan["reference"] = {"filename": reference["filename"], "pages": sorted(set(pages))}
    problems = validate_plan(plan, hours, weeks).errors
    if problems:
        raise ProgressImportError("The saved roadmap is not valid: " + " ".join(problems[:3]))

    profile = LearnerProfile.from_dict(data.get("profile")).to_dict()
    profile["hours_per_week"], profile["duration_weeks"] = hours, weeks

    imported_tasks = data.get("tasks") if isinstance(data.get("tasks"), list) else []
    tasks = tasks_from_plan(plan)
    done_by_key = {
        _key(t.get("week"), t.get("name", "")): bool(t.get("done"))
        for t in imported_tasks
        if isinstance(t, dict) and t.get("source") == "plan"
    }
    for task in tasks:
        task["done"] = done_by_key.get(_key(task["week"], task["name"]), False)
    for item in imported_tasks:
        if not (isinstance(item, dict) and item.get("source") == "custom"):
            continue
        week = item.get("week")
        if isinstance(week, bool) or not isinstance(week, int) or not 1 <= week <= MAX_WEEKS:
            week = None
        added, _ = add_custom_task(tasks, str(item.get("name", "")), week)
        if added:
            tasks[-1]["done"] = bool(item.get("done"))

    version = data.get("plan_version")
    return {
        "plan": plan,
        "profile": profile,
        "tasks": tasks,
        "plan_version": version if isinstance(version, int) and version > 0 else 1,
        "pdf_filename": data.get("pdf_filename") if isinstance(data.get("pdf_filename"), str) else None,
    }


# ==========================================================================
# Session state transitions
# ==========================================================================
def initial_state() -> dict:
    return {
        "roadmap_plan": None,
        "plan_profile": None,
        "plan_version": 0,
        "plan_warnings": [],
        "plan_notes": [],
        "tasks": [],
        "messages": [],
        "pending_revision": None,
        "link_results": {},
        "links_checked_on": None,
        "epoch": 0,  # bumps whenever tasks are rebuilt, so old checkbox widgets are not reused
        "pdf_index": None,
        "queued_question": None,
        "failed_question": None,
    }


def _bump_epoch(state: MutableMapping) -> None:
    state["epoch"] = int(state.get("epoch") or 0) + 1


def init_state(state: MutableMapping) -> None:
    for key, value in initial_state().items():
        if key not in state:
            state[key] = value


def load_plan(state: MutableMapping, plan: dict, profile: dict, *, warnings=(), notes=()) -> None:
    """Install a freshly generated roadmap and reset everything that depended on the old one."""
    state["roadmap_plan"] = plan
    state["plan_profile"] = dict(profile)
    state["plan_version"] = 1
    state["plan_warnings"] = list(warnings)
    state["plan_notes"] = list(notes)
    state["tasks"] = tasks_from_plan(plan)
    state["messages"] = []
    state["pending_revision"] = None
    state["failed_question"] = None
    _bump_epoch(state)


def load_imported(state: MutableMapping, imported: dict) -> None:
    state["roadmap_plan"] = imported["plan"]
    state["plan_profile"] = imported["profile"]
    state["plan_version"] = imported["plan_version"]
    state["plan_warnings"] = []
    state["plan_notes"] = ["Restored from a saved progress file."]
    state["tasks"] = imported["tasks"]
    state["messages"] = []
    state["pending_revision"] = None
    state["failed_question"] = None
    _bump_epoch(state)


def stage_revision(state: MutableMapping, revision: RevisionResult, instruction: str) -> None:
    """Hold a drafted revision for review. The displayed roadmap does NOT change yet."""
    state["pending_revision"] = {
        "plan": revision.plan,
        "change_summary": list(revision.change_summary),
        "changed_weeks": list(revision.changed_weeks),
        "warnings": list(revision.warnings),
        "notes": list(revision.notes),
        "instruction": instruction,
    }


def discard_pending_revision(state: MutableMapping) -> None:
    state["pending_revision"] = None


def apply_pending_revision(state: MutableMapping) -> str:
    """Make the drafted revision the roadmap everywhere: display, download, tracker."""
    pending = state.get("pending_revision")
    if not pending:
        raise ValueError("There is no drafted revision to apply.")
    new_plan = pending["plan"]
    constraints = new_plan["constraints"]

    profile = dict(state.get("plan_profile") or {})
    profile["hours_per_week"] = constraints["hours_per_week"]
    profile["duration_weeks"] = constraints["duration_weeks"]

    state["roadmap_plan"] = new_plan
    state["plan_profile"] = profile
    state["plan_version"] = int(state.get("plan_version") or 1) + 1
    state["plan_warnings"] = list(pending["warnings"])
    state["plan_notes"] = list(pending["notes"])
    state["tasks"] = merge_tasks(state.get("tasks", []), tasks_from_plan(new_plan))
    state["pending_revision"] = None
    _bump_epoch(state)

    summary = "\n".join(f"- {line}" for line in pending["change_summary"])
    message = f"✅ Revised roadmap applied (version {state['plan_version']}).\n{summary}"
    state["messages"] = list(state.get("messages", [])) + [
        {"role": "assistant", "content": message, "kind": "note"}
    ]
    return message


def reset_progress(state: MutableMapping) -> None:
    for task in state.get("tasks", []):
        task["done"] = False
    _bump_epoch(state)


def plan_markdown_for_state(state: MutableMapping, checked_on: str | None = None) -> str:
    """The Markdown for the current roadmap (used for display and download)."""
    plan = state.get("roadmap_plan")
    if not plan:
        return ""
    return plan_to_markdown(
        plan, state.get("plan_profile"), state.get("link_results") or None, checked_on=checked_on
    )

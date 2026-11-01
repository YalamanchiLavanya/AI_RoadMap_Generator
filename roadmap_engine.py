"""Roadmap generation, streaming with safe retries, validation, and revision.

Design notes
------------
* The model returns the roadmap as structured JSON. The app validates that data
  (week count, per-week hours, required sections, milestones, feasibility) before
  anything is shown, so limits no longer depend on prompting alone.
* Streaming retries only happen *before* any text has been emitted. If a stream
  breaks after text has appeared, ``StreamInterruptedError`` carries the partial
  text and nothing is silently restarted behind the reader's back.
* The Markdown shown in the app and the Markdown that is downloaded come from the
  same function (``plan_to_markdown``), so they cannot drift apart.
"""
from __future__ import annotations

import json
import math
import re
import time
from dataclasses import dataclass, field
from typing import Callable, Iterator

import prompts
from config import (
    ACTIVITY_TYPES,
    MAX_HOURS_PER_WEEK,
    MAX_WEEKS,
    MIN_HOURS_PER_WEEK,
    MIN_WEEKS,
    LearnerProfile,
    Settings,
)
from link_checker import resource_cells

_EPS = 1e-6


# ==========================================================================
# Errors
# ==========================================================================
class GenerationError(RuntimeError):
    """The model call failed. ``str(error)`` is safe to show to the learner."""

    def __init__(self, message: str, *, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


class EmptyResponseError(RuntimeError):
    """The model answered with no text."""


class StreamInterruptedError(RuntimeError):
    """A stream failed after some text had already been emitted."""

    def __init__(self, partial_text: str, cause: BaseException):
        super().__init__(f"The response stream was interrupted: {cause}")
        self.partial_text = partial_text
        self.cause = cause


class PlanParseError(ValueError):
    """The reply could not be read as a JSON object."""


class PlanValidationError(ValueError):
    """The plan broke the rules and could not be repaired."""

    def __init__(self, errors: list[str], warnings: list[str] | None = None):
        super().__init__("; ".join(errors))
        self.errors = errors
        self.warnings = warnings or []


# ==========================================================================
# Error classification
# ==========================================================================
_RETRYABLE_CODES = {408, 429, 500, 502, 503, 504}
_RETRYABLE_TERMS = (
    "rate limit", "resource_exhausted", "unavailable", "overloaded",
    "timed out", "timeout", "connection reset", "connection aborted", "temporarily",
)


def _status_code(exc: BaseException) -> int | None:
    for attribute in ("code", "status_code"):
        value = getattr(exc, attribute, None)
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    match = re.search(r"\b([45]\d\d)\b", str(exc))
    return int(match.group(1)) if match else None


def is_retryable_error(exc: BaseException) -> bool:
    if isinstance(exc, EmptyResponseError):
        return True
    code = _status_code(exc)
    if code is not None:
        return code in _RETRYABLE_CODES
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return True
    text = str(exc).lower()
    return any(term in text for term in _RETRYABLE_TERMS)


def friendly_error_message(exc: BaseException) -> str:
    if isinstance(exc, EmptyResponseError):
        return "Gemini returned an empty response. Check the model name and API quota, then try again."
    code = _status_code(exc)
    text = str(exc).lower()
    if code in (401, 403) or "api key" in text or "permission_denied" in text:
        return "The Gemini API key was rejected. Check GEMINI_API_KEY in your secrets or .env file."
    if code == 404 or "is not found" in text or "not_found" in text:
        return "The Gemini model was not found. Check GEMINI_MODEL in your secrets or .env file."
    if code == 429 or "resource_exhausted" in text or "quota" in text or "rate limit" in text:
        return "The Gemini rate limit or quota was reached. Wait a minute and try again, or check your API quota."
    if code in (500, 502, 503, 504) or "unavailable" in text or "overloaded" in text:
        return "The Gemini service is temporarily unavailable. Please try again in a moment."
    if isinstance(exc, (TimeoutError, ConnectionError)) or "timed out" in text or "connection" in text:
        return "A network problem stopped the request from reaching Gemini. Check your connection and try again."
    return f"The Gemini request failed: {str(exc)[:200]}"


# ==========================================================================
# Talking to the model
# ==========================================================================
def split_messages(messages: list[dict]) -> tuple[str, list[dict]]:
    """Convert chat messages to (system_text, Gemini contents).

    Consecutive messages with the same role are merged, because several of the
    prompts send more than one user message in a row.
    """
    system_parts: list[str] = []
    contents: list[dict] = []
    for message in messages:
        content = (message.get("content") or "").strip()
        if not content:
            continue
        role = message.get("role", "user")
        if role == "system":
            system_parts.append(content)
            continue
        gemini_role = "model" if role == "assistant" else "user"
        if contents and contents[-1]["role"] == gemini_role:
            contents[-1]["parts"][0]["text"] += "\n\n" + content
        else:
            contents.append({"role": gemini_role, "parts": [{"text": content}]})
    return "\n\n".join(system_parts), contents


def _backoff_seconds(attempt: int) -> float:
    return float(min(2 ** (attempt - 1), 8))


def generate_response(
    client,
    messages: list[dict],
    *,
    settings: Settings,
    stream: bool = True,
    json_mode: bool = False,
    max_tokens: int | None = None,
    temperature: float | None = None,
    max_attempts: int = 3,
    sleep: Callable[[float], None] = time.sleep,
) -> Iterator[str]:
    """Yield the model's answer as text pieces.

    Retry rule: a failed call is retried automatically ONLY if no text has been
    yielded yet. Once text has been emitted, restarting would repeat the answer, so
    ``StreamInterruptedError`` (with the partial text) is raised instead.
    """
    system_text, contents = split_messages(messages)
    if not contents:
        raise ValueError("No user message was provided to the model.")

    config: dict = {
        "max_output_tokens": max_tokens or settings.max_output_tokens,
        "temperature": settings.temperature if temperature is None else temperature,
    }
    if system_text:
        config["system_instruction"] = system_text
    if json_mode:
        config["response_mime_type"] = "application/json"

    for attempt in range(1, max_attempts + 1):
        emitted: list[str] = []
        try:
            if stream:
                pieces = client.models.generate_content_stream(
                    model=settings.model, contents=contents, config=config
                )
                for chunk in pieces:
                    text = getattr(chunk, "text", None)
                    if text:
                        emitted.append(text)
                        yield text
            else:
                response = client.models.generate_content(
                    model=settings.model, contents=contents, config=config
                )
                text = getattr(response, "text", None)
                if text and text.strip():
                    emitted.append(text)
                    yield text
            if not emitted:
                raise EmptyResponseError("empty response")
            return
        except Exception as exc:  # noqa: BLE001 - classified below
            if emitted:
                raise StreamInterruptedError("".join(emitted), exc) from exc
            retryable = is_retryable_error(exc)
            if retryable and attempt < max_attempts:
                sleep(_backoff_seconds(attempt))
                continue
            raise GenerationError(friendly_error_message(exc), retryable=retryable) from exc


def collect_text(
    client,
    messages: list[dict],
    *,
    settings: Settings,
    on_chunk: Callable[[str], None] | None = None,
    on_reset: Callable[[], None] | None = None,
    max_restarts: int = 1,
    **kwargs,
) -> str:
    """Run a call to completion and return the full text.

    If the stream breaks part-way, the partial text is DISCARDED (``on_reset`` lets
    the UI clear what it showed) and the request starts again from a clean slate, so
    the final text never contains a repeated section.
    """
    restarts = 0
    while True:
        parts: list[str] = []
        try:
            for piece in generate_response(client, messages, settings=settings, **kwargs):
                parts.append(piece)
                if on_chunk:
                    on_chunk("".join(parts))
            return "".join(parts)
        except StreamInterruptedError:
            if restarts >= max_restarts:
                raise
            restarts += 1
            if on_reset:
                on_reset()


# ==========================================================================
# Parsing and normalising the model's JSON
# ==========================================================================
def extract_json(text: str) -> dict:
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\s*", "", cleaned)
        cleaned = re.sub(r"\s*```\s*$", "", cleaned)
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end <= start:
        raise PlanParseError("no JSON object found in the reply")
    try:
        data = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as exc:
        raise PlanParseError(f"line {exc.lineno}, column {exc.colno}: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise PlanParseError("the JSON is not an object")
    return data


def _clean_str(value) -> str:
    if value is None:
        return ""
    return value.strip() if isinstance(value, str) else str(value).strip()


def _to_float(value, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value) if math.isfinite(value) else default
    if isinstance(value, str):
        match = re.search(r"-?\d+(?:\.\d+)?", value.replace(",", "."))
        if match:
            return float(match.group())
    return default


def _to_int(value, default: int | None = None) -> int | None:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return int(value)
    if isinstance(value, str):
        match = re.search(r"-?\d+", value)
        if match:
            return int(match.group())
    return default


def _str_list(value) -> list[str]:
    if isinstance(value, str):
        value = [line.strip(" -•\t") for line in value.splitlines()]
    if not isinstance(value, list):
        return []
    return [text for text in (_clean_str(item) for item in value) if text]


def normalize_plan(raw: dict) -> tuple[dict, list[str]]:
    """Coerce loosely-typed model output into the plan structure.

    Missing required sections are NOT invented here - they are left out so that
    ``validate_plan`` reports them.
    """
    notes: list[str] = []
    plan: dict = {}

    feasibility = raw.get("feasibility")
    if isinstance(feasibility, dict):
        realistic = feasibility.get("realistic")
        if isinstance(realistic, str):
            realistic = realistic.strip().lower() in ("true", "yes")
        plan["feasibility"] = {
            "realistic": realistic if isinstance(realistic, bool) else None,
            "summary": _clean_str(feasibility.get("summary")),
            "achievable_outcome": _clean_str(feasibility.get("achievable_outcome")),
        }

    plan["overview"] = _clean_str(raw.get("overview"))
    plan["skill_assessment"] = _clean_str(raw.get("skill_assessment"))
    plan["skill_gaps"] = _str_list(raw.get("skill_gaps"))

    weeks: list[dict] = []
    raw_weeks = raw.get("weeks")
    for position, item in enumerate(raw_weeks if isinstance(raw_weeks, list) else [], start=1):
        if not isinstance(item, dict):
            continue
        number = _to_int(item.get("week"))
        if number is None:
            number = position
            notes.append(f"Week {position} had no week number; numbered by position.")
        activities = []
        for activity in item.get("activities") if isinstance(item.get("activities"), list) else []:
            if not isinstance(activity, dict):
                continue
            kind = _clean_str(activity.get("type")).lower()
            if kind not in ACTIVITY_TYPES:
                kind = "learn"
            activities.append(
                {
                    "task": _clean_str(activity.get("task")),
                    "type": kind,
                    "hours": round(_to_float(activity.get("hours")), 2),
                }
            )
        resources = []
        for resource in item.get("resources") if isinstance(item.get("resources"), list) else []:
            if not isinstance(resource, dict) or not _clean_str(resource.get("title")):
                continue
            url = _clean_str(resource.get("url"))
            resources.append(
                {
                    "title": _clean_str(resource.get("title")),
                    "provider": _clean_str(resource.get("provider")),
                    "url": None if url.lower() in ("", "null", "none", "n/a") else url,
                }
            )
        pages: list[int] = []
        if isinstance(item.get("source_pages"), list):
            for raw_page in item["source_pages"]:
                page = _to_int(raw_page)
                if page and page > 0:
                    pages.append(page)
        weeks.append(
            {
                "week": number,
                "title": _clean_str(item.get("title")),
                "focus": _clean_str(item.get("focus")),
                "activities": activities,
                "milestone": _clean_str(item.get("milestone")),
                "resources": resources,
                "source_pages": sorted(set(pages)),
            }
        )
    plan["weeks"] = weeks

    project = raw.get("portfolio_project")
    if isinstance(project, dict):
        plan["portfolio_project"] = {
            "title": _clean_str(project.get("title")),
            "description": _clean_str(project.get("description")),
            "deliverables": _str_list(project.get("deliverables")),
        }
    plan["next_steps"] = _str_list(raw.get("next_steps"))

    constraints = raw.get("constraints")
    if isinstance(constraints, dict):
        plan["constraints"] = {
            "hours_per_week": _to_int(constraints.get("hours_per_week")),
            "duration_weeks": _to_int(constraints.get("duration_weeks")),
        }
    if "change_summary" in raw:
        plan["change_summary"] = _str_list(raw.get("change_summary"))
    return plan, notes


def week_hours(week: dict) -> float:
    return round(sum(_to_float(a.get("hours")) for a in week.get("activities", [])), 2)


def fit_hours_to_budget(plan: dict, budget: float, max_overage: float = 0.15) -> list[str]:
    """Scale activity hours down when a week is only slightly over the limit.

    LLMs often add up hours slightly wrong. A small overage is fixed
    deterministically (and reported); a large one is left for validation to reject.
    """
    notes: list[str] = []
    for week in plan.get("weeks", []):
        total = week_hours(week)
        if budget + _EPS < total <= budget * (1 + max_overage) + _EPS:
            scale = budget / total
            for activity in week["activities"]:
                activity["hours"] = max(0.25, math.floor(activity["hours"] * scale * 4) / 4)
            notes.append(
                f"Week {week['week']}: activity hours were scaled from {total:g} h to "
                f"{week_hours(week):g} h to fit the {budget:g} h weekly limit."
            )
    return notes


# ==========================================================================
# Validation
# ==========================================================================
@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def validate_plan(plan, hours_per_week, duration_weeks) -> ValidationResult:
    """Check a plan against the learner's limits and the required sections."""
    result = ValidationResult()
    error, warn = result.errors.append, result.warnings.append

    if not isinstance(plan, dict):
        error("The plan is not a JSON object.")
        return result

    if not isinstance(hours_per_week, (int, float)) or not MIN_HOURS_PER_WEEK <= hours_per_week <= MAX_HOURS_PER_WEEK:
        error(f"Hours per week must be between {MIN_HOURS_PER_WEEK} and {MAX_HOURS_PER_WEEK}.")
        return result
    if not isinstance(duration_weeks, int) or not MIN_WEEKS <= duration_weeks <= MAX_WEEKS:
        error(f"Duration must be between {MIN_WEEKS} and {MAX_WEEKS} weeks.")
        return result

    # --- feasibility -------------------------------------------------------
    feasibility = plan.get("feasibility")
    if not isinstance(feasibility, dict):
        error('Missing "feasibility" (realistic, summary, achievable_outcome).')
    else:
        if not isinstance(feasibility.get("realistic"), bool):
            error('"feasibility.realistic" must be true or false.')
        if not _clean_str(feasibility.get("summary")):
            error('"feasibility.summary" is empty.')
        if feasibility.get("realistic") is False and not _clean_str(feasibility.get("achievable_outcome")):
            error('The goal was marked unrealistic but "feasibility.achievable_outcome" is empty.')

    # --- required text sections -------------------------------------------
    if not _clean_str(plan.get("overview")):
        error('Missing "overview".')
    if not _clean_str(plan.get("skill_assessment")):
        error('Missing "skill_assessment".')
    if not plan.get("skill_gaps"):
        error('"skill_gaps" is empty.')
    project = plan.get("portfolio_project")
    if not isinstance(project, dict) or not _clean_str(project.get("title")) or not _clean_str(project.get("description")):
        error('"portfolio_project" needs a title and a description.')
    if not plan.get("next_steps"):
        error('"next_steps" is empty.')

    # --- weeks --------------------------------------------------------------
    weeks = plan.get("weeks")
    if not isinstance(weeks, list) or not weeks:
        error("The plan has no weeks.")
        return result
    if len(weeks) != duration_weeks:
        error(f"Expected exactly {duration_weeks} weeks but the plan has {len(weeks)}.")
    numbers = [w.get("week") for w in weeks]
    if numbers != list(range(1, len(weeks) + 1)):
        error(f"Week numbers must run 1..{len(weeks)} in order (found {numbers}).")

    resource_count = 0
    for position, week in enumerate(weeks, start=1):
        label = f"Week {week.get('week', position)}"
        if not _clean_str(week.get("title")):
            error(f"{label} has no title.")
        if not _clean_str(week.get("milestone")):
            error(f"{label} has no milestone.")
        activities = week.get("activities") or []
        if not activities:
            error(f"{label} has no activities.")
            continue
        for index, activity in enumerate(activities, start=1):
            if not _clean_str(activity.get("task")):
                error(f"{label}, activity {index} has no task description.")
            hours = _to_float(activity.get("hours"))
            if hours <= 0:
                error(f"{label}, activity {index} needs hours greater than 0.")
        total = week_hours(week)
        if total > hours_per_week + _EPS:
            error(f"{label} uses {total:g} h but the weekly limit is {hours_per_week:g} h.")
        elif total < hours_per_week * 0.5:
            warn(f"{label} uses only {total:g} h of the {hours_per_week:g} h available.")
        resources = week.get("resources") or []
        resource_count += len(resources)
        if not resources:
            warn(f"{label} lists no resources.")

    if resource_count == 0:
        error("The plan lists no learning resources.")
    return result


def assess_time_budget(profile: LearnerProfile) -> str | None:
    """A rough, deterministic check of whether the total hours look too small.

    This is a rule of thumb, not a fact: it only decides whether the model is told
    to take extra care over feasibility, and whether the app asks for a second look.
    """
    job_ready_words = (
        "become", "job", "career", "hired", "professional", "engineer", "developer",
        "analyst", "scientist", "expert", "master", "certified", "certification",
    )
    minimum_hours = {"Beginner": 250, "Intermediate": 120, "Advanced": 60}
    goal = profile.goal.lower()
    if not any(re.search(rf"\b{re.escape(word)}", goal) for word in job_ready_words):
        return None
    needed = minimum_hours.get(profile.level, 250)
    if profile.total_hours >= needed:
        return None
    return (
        f"The learner has {profile.total_hours} hours in total. As a rough rule of thumb, "
        f"reaching a job-ready level for a goal like this often takes {needed}+ hours at the "
        f"{profile.level} level, so the full goal is probably NOT realistic. Set "
        f"feasibility.realistic to false, explain what is achievable in {profile.total_hours} "
        f"hours, and plan toward that."
    )


# ==========================================================================
# Producing a validated plan (generation and revision share this)
# ==========================================================================
@dataclass
class PlanResult:
    plan: dict
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    repaired: bool = False
    time_note: str | None = None


@dataclass
class RevisionResult(PlanResult):
    change_summary: list[str] = field(default_factory=list)
    changed_weeks: list[int] = field(default_factory=list)


def _produce_plan(
    client,
    messages: list[dict],
    *,
    settings: Settings,
    fixed_targets: tuple[int, int] | None,
    default_constraints: dict,
    on_chunk=None,
    on_reset=None,
    on_status=None,
    sleep=time.sleep,
    max_repairs: int = 1,
) -> tuple[dict, list[str], list[str], bool]:
    conversation = list(messages)
    errors: list[str] = []
    warnings: list[str] = []

    for attempt in range(max_repairs + 1):
        if attempt > 0:
            if on_status:
                on_status("Fixing problems found while checking the plan...")
            if on_reset:
                on_reset()
        try:
            text = collect_text(
                client, conversation, settings=settings, on_chunk=on_chunk,
                on_reset=on_reset, json_mode=True, sleep=sleep,
            )
        except StreamInterruptedError as exc:
            raise GenerationError(
                "The connection dropped while the roadmap was being written. "
                "Nothing was saved - please try again.",
                retryable=True,
            ) from exc

        if on_status:
            on_status("Checking the plan against your limits...")
        try:
            plan, notes = normalize_plan(extract_json(text))
        except PlanParseError as exc:
            errors = [f"The reply was not valid JSON ({exc}); it may have been cut off."]
            conversation = conversation + [{"role": "user", "content": prompts.build_repair_prompt(errors)}]
            continue

        if fixed_targets:
            hours, weeks = fixed_targets
        else:
            constraints = plan.get("constraints") or {}
            hours = constraints.get("hours_per_week") or default_constraints["hours_per_week"]
            weeks = constraints.get("duration_weeks") or default_constraints["duration_weeks"]
        plan["constraints"] = {"hours_per_week": hours, "duration_weeks": weeks}

        if isinstance(hours, int):
            notes += fit_hours_to_budget(plan, hours)
        validation = validate_plan(plan, hours, weeks)
        if validation.ok:
            return plan, validation.warnings, notes, attempt > 0

        errors, warnings = validation.errors, validation.warnings
        conversation = conversation + [
            {"role": "assistant", "content": json.dumps(plan, ensure_ascii=False)},
            {"role": "user", "content": prompts.build_repair_prompt(errors)},
        ]

    raise PlanValidationError(errors, warnings)


def _restrict_source_pages(plan: dict, allowed_pages: set[int]) -> None:
    """Keep only page numbers that really came from the document."""
    for week in plan.get("weeks", []):
        week["source_pages"] = [p for p in week.get("source_pages", []) if p in allowed_pages]


def generate_roadmap(
    client,
    profile: LearnerProfile,
    *,
    settings: Settings,
    hits: list[dict] | None = None,
    on_chunk=None,
    on_reset=None,
    on_status=None,
    sleep=time.sleep,
) -> PlanResult:
    problems = profile.problems()
    if problems:
        raise ValueError(" ".join(problems))

    time_note = assess_time_budget(profile)
    prompt = prompts.build_roadmap_prompt(profile, time_note, hits)
    messages = prompts.build_roadmap_messages(prompt)
    plan, warnings, notes, repaired = _produce_plan(
        client, messages, settings=settings,
        fixed_targets=(profile.hours_per_week, profile.duration_weeks),
        default_constraints={"hours_per_week": profile.hours_per_week, "duration_weeks": profile.duration_weeks},
        on_chunk=on_chunk, on_reset=on_reset, on_status=on_status, sleep=sleep,
    )
    plan.pop("change_summary", None)

    if hits:
        pages = {int(h["page"]) for h in hits}
        plan["reference"] = {"filename": hits[0]["source"], "pages": sorted(pages)}
        _restrict_source_pages(plan, pages)
    else:
        _restrict_source_pages(plan, set())

    if time_note and plan["feasibility"]["realistic"] is True:
        warnings.append(
            "The time available looks small for this goal, yet the plan was marked realistic. "
            "Review the scope before relying on it."
        )
    return PlanResult(plan=plan, warnings=warnings, notes=notes, repaired=repaired, time_note=time_note)


def diff_weeks(old_plan: dict, new_plan: dict) -> list[int]:
    """Week numbers whose content differs between two plans."""
    old = {w["week"]: w for w in old_plan.get("weeks", [])}
    new = {w["week"]: w for w in new_plan.get("weeks", [])}
    changed = []
    for number in sorted(set(old) | set(new)):
        if json.dumps(old.get(number), sort_keys=True) != json.dumps(new.get(number), sort_keys=True):
            changed.append(number)
    return changed


def revise_roadmap(
    client,
    plan: dict,
    profile: dict,
    instruction: str,
    *,
    settings: Settings,
    history: list[dict] | None = None,
    progress_text: str = "",
    hits: list[dict] | None = None,
    on_chunk=None,
    on_reset=None,
    on_status=None,
    sleep=time.sleep,
) -> RevisionResult:
    """Ask the model for a full revised plan. The caller decides whether to apply it."""
    if not (instruction or "").strip():
        raise ValueError("Describe what should change in the roadmap.")

    current = dict(plan.get("constraints") or {})
    current.setdefault("hours_per_week", profile.get("hours_per_week"))
    current.setdefault("duration_weeks", profile.get("duration_weeks"))
    plan_for_prompt = {**plan, "constraints": current}
    plan_for_prompt.pop("reference", None)

    prompt = prompts.build_revision_prompt(
        plan_for_prompt, profile, instruction,
        progress_text=progress_text, conversation=history, hits=hits,
    )
    messages = prompts.build_roadmap_messages(prompt)
    revised, warnings, notes, repaired = _produce_plan(
        client, messages, settings=settings, fixed_targets=None, default_constraints=current,
        on_chunk=on_chunk, on_reset=on_reset, on_status=on_status, sleep=sleep,
    )
    summary = revised.pop("change_summary", []) or [
        "The model did not list its changes - compare the preview with your current roadmap."
    ]

    allowed_pages = {int(h["page"]) for h in (hits or [])}
    reference = plan.get("reference")
    if reference:
        allowed_pages |= {int(p) for p in reference.get("pages", [])}
        revised["reference"] = reference
    _restrict_source_pages(revised, allowed_pages)

    return RevisionResult(
        plan=revised, warnings=warnings, notes=notes, repaired=repaired,
        change_summary=summary, changed_weeks=diff_weeks(plan, revised),
    )


# ==========================================================================
# Presenting a plan
# ==========================================================================
def collect_urls(plan: dict) -> list[str]:
    urls: list[str] = []
    for week in plan.get("weeks", []):
        for resource in week.get("resources", []):
            url = resource.get("url")
            if isinstance(url, str) and url.strip() and url.strip() not in urls:
                urls.append(url.strip())
    return urls


def stream_progress(text: str, total_weeks: int) -> float:
    """Rough 0..0.95 progress while JSON streams in, from the weeks seen so far."""
    seen = len(re.findall(r'"week"\s*:', text))
    return min(0.95, seen / max(total_weeks, 1))


def plan_check_summary(plan: dict) -> str:
    constraints = plan.get("constraints", {})
    weeks = plan.get("weeks", [])
    busiest = max((week_hours(w) for w in weeks), default=0)
    milestones = sum(1 for w in weeks if w.get("milestone"))
    return (
        f"✅ Checked: {len(weeks)} weeks · busiest week {busiest:g} h "
        f"(limit {constraints.get('hours_per_week')} h) · {milestones} milestones"
    )


def plan_outline(plan: dict) -> str:
    """Compact text version of a plan for the coach prompt."""
    if not plan:
        return ""
    lines = []
    feasibility = plan.get("feasibility") or {}
    if feasibility:
        lines.append(f"Feasibility: {'realistic' if feasibility.get('realistic') else 'NOT fully realistic'} - {feasibility.get('summary', '')}")
        if feasibility.get("achievable_outcome"):
            lines.append(f"Achievable outcome: {feasibility['achievable_outcome']}")
    constraints = plan.get("constraints") or {}
    lines.append(f"Limits: {constraints.get('hours_per_week')} h/week for {constraints.get('duration_weeks')} weeks")
    for week in plan.get("weeks", []):
        lines.append(f"Week {week['week']}: {week.get('title', '')} ({week_hours(week):g} h) - {week.get('focus', '')}")
        for activity in week.get("activities", []):
            lines.append(f"  - [{activity['type']}] {activity['task']} ({activity['hours']:g} h)")
        lines.append(f"  Milestone: {week.get('milestone', '')}")
    project = plan.get("portfolio_project") or {}
    if project:
        lines.append(f"Portfolio project: {project.get('title', '')} - {project.get('description', '')}")
    return "\n".join(lines)


def _cell(text) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ").strip()


def plan_to_markdown(
    plan: dict,
    profile: dict | None = None,
    link_results: dict | None = None,
    *,
    checked_on: str | None = None,
) -> str:
    """The single Markdown rendering used for display AND download."""
    profile = profile or {}
    constraints = plan.get("constraints", {})
    hours, weeks_count = constraints.get("hours_per_week"), constraints.get("duration_weeks")
    lines = [f"# Learning Roadmap: {profile.get('goal') or 'Your goal'}", ""]
    meta = []
    if profile.get("level"):
        meta.append(f"**Level:** {profile['level']}")
    if hours and weeks_count:
        meta.append(f"**Time:** {hours} h/week × {weeks_count} weeks ({hours * weeks_count} h)")
    if profile.get("learning_style"):
        meta.append(f"**Style:** {profile['learning_style']}")
    if meta:
        lines += [" · ".join(meta), ""]

    reference = plan.get("reference")
    if reference:
        pages = ", ".join(str(p) for p in reference.get("pages", []))
        lines += [f"*Aligned with your uploaded document **{reference.get('filename')}** (pages {pages}).*", ""]

    feasibility = plan.get("feasibility") or {}
    if feasibility.get("realistic") is False:
        lines += [
            "> ⚠️ **Reality check - this goal is not fully achievable in the time available.**",
            f"> {_cell(feasibility.get('summary', ''))}",
            f"> **What you can reasonably achieve:** {_cell(feasibility.get('achievable_outcome', ''))}",
            "",
        ]
    elif feasibility.get("summary"):
        lines += [f"> ✅ {_cell(feasibility['summary'])}", ""]

    lines += ["## 1. Goal Overview", plan.get("overview", ""), ""]
    lines += ["## 2. Current Skill Assessment", plan.get("skill_assessment", ""), ""]
    lines += ["## 3. Skill Gaps"] + [f"- {gap}" for gap in plan.get("skill_gaps", [])] + [""]

    lines += ["## 4. Week-by-Week Learning Plan", ""]
    for week in plan.get("weeks", []):
        lines.append(f"### Week {week['week']} - {week.get('title', '')}  ({week_hours(week):g} h)")
        if week.get("focus"):
            lines.append(f"*{week['focus']}*")
        lines += ["", "| Task | Type | Hours |", "|---|---|---|"]
        for activity in week.get("activities", []):
            lines.append(f"| {_cell(activity['task'])} | {activity['type']} | {activity['hours']:g} |")
        lines.append("")
        lines.append(f"**Milestone:** {week.get('milestone', '')}")
        if week.get("source_pages") and reference:
            pages = ", ".join(f"p. {p}" for p in week["source_pages"])
            lines.append(f"*Document reference: {reference.get('filename')}, {pages}*")
        lines.append("")

    lines += ["## 5. Learning Resources", ""]
    note = "Only links marked ✅ answered when they were checked"
    note += f" on {checked_on}." if checked_on else "."
    lines += [
        f"{note} Other entries are suggestions: search for the exact title and check the source yourself.",
        "",
        "| Week | Resource | Provider | Link check |",
        "|---|---|---|---|",
    ]
    any_resource = False
    for week in plan.get("weeks", []):
        for resource in week.get("resources", []):
            any_resource = True
            title_cell, status_cell = resource_cells(resource, link_results)
            lines.append(
                f"| {week['week']} | {_cell(title_cell)} | {_cell(resource.get('provider', ''))} | {_cell(status_cell)} |"
            )
    if not any_resource:
        lines.append("| - | No resources listed | - | - |")
    lines.append("")

    project = plan.get("portfolio_project") or {}
    lines += ["## 6. Portfolio Project", f"**{project.get('title', '')}** - {project.get('description', '')}"]
    lines += [f"- {item}" for item in project.get("deliverables", [])] + [""]

    lines += ["## 7. Weekly Progress Checkpoints", "", "| Week | Checkpoint |", "|---|---|"]
    for week in plan.get("weeks", []):
        lines.append(f"| {week['week']} | {_cell(week.get('milestone', ''))} |")
    lines.append("")

    lines += ["## 8. Next Steps"] + [f"- {step}" for step in plan.get("next_steps", [])] + [""]
    return "\n".join(lines)

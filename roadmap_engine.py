
import re
import time

from google.genai import types
from config import create_client, get_model_name
from prompts import SYSTEM_PROMPT, build_roadmap_prompt


# Convert learner details into a prompt message
def build_roadmap_messages(
    goal,
    current_skills,
    level,
    hours_per_week,
    duration_weeks,
    learning_style="Hands-on practice",
    learning_language="English",
    retrieved_context="",
):
    user_prompt = build_roadmap_prompt(
        goal=goal,
        current_skills=current_skills,
        level=level,
        hours_per_week=hours_per_week,
        duration_weeks=duration_weeks,
        learning_style=learning_style,
        learning_language=learning_language,
        retrieved_context=retrieved_context,
    )

    return [
        {
            "role": "user",
            "content": user_prompt,
        }
    ]


# Generate a response with streaming and safe retries
def generate_response(
    messages,
    stream=True,
    max_tokens=3500,
    client=None,
    max_retries=2,
):
    if client is None:
        client = create_client()

    # Convert messages into Gemini-compatible content
    contents = []

    for message in messages:
        role = message.get("role", "user")
        content = message.get("content", "")

        if role == "assistant":
            role = "model"

        contents.append(
            types.Content(
                role=role,
                parts=[
                    types.Part.from_text(text=str(content))
                ],
            )
        )

    generation_config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        max_output_tokens=max_tokens,
        temperature=0.4,
    )

    attempt = 0

    while True:
        # Each attempt starts before any text has been yielded
        emitted_text = False

        try:
            if stream:
                response_stream = client.models.generate_content_stream(
                    model=get_model_name(),
                    contents=contents,
                    config=generation_config,
                )

                for chunk in response_stream:
                    text_chunk = getattr(chunk, "text", None)

                    if text_chunk:
                        emitted_text = True
                        yield text_chunk

                return

            # Non-streaming response
            response = client.models.generate_content(
                model=get_model_name(),
                contents=contents,
                config=generation_config,
            )

            if response.text:
                yield response.text

            return

        except Exception as error:
            # Never retry a partially emitted response.
            # This prevents duplicated text in the UI.
            if emitted_text:
                raise RuntimeError(
                    "The response stream was interrupted after text "
                    "was generated. Please generate a fresh response. "
                    "The partial response was not retried."
                ) from error

            # Retry only before any text has been emitted
            if attempt >= max_retries:
                raise RuntimeError(
                    f"Gemini API error: {type(error).__name__}: {error}"
                ) from error

            attempt += 1
            time.sleep(attempt)


# Validate the generated roadmap
def validate_roadmap(roadmap, duration_weeks, hours_per_week):
    warnings = []

    # Normalize whitespace for section checks
    normalized_roadmap = re.sub(
        r"\s+", " ", roadmap
    ).lower()

    required_sections = {
        "Goal Overview": [
            "goal overview",
        ],
        "Current Skill Assessment": [
            "current skill assessment",
            "current skills assessment",
            "skill assessment",
        ],
        "Skill Gaps": [
            "skill gaps",
            "skills gaps",
            "skill gap analysis",
        ],
        "Week-by-Week Learning Plan": [
            "week-by-week learning plan",
            "week by week learning plan",
            "weekly learning plan",
            "week-by-week plan",
        ],
        "Practical Exercises": [
            "practical exercises",
            "practice exercises",
            "hands-on exercises",
        ],
        "Learning Resources": [
            "learning resources",
            "recommended resources",
            "resources and references",
        ],
        "Portfolio Project": [
            "portfolio project",
            "capstone project",
            "final project",
        ],
        "Weekly Milestones and Checkpoints": [
            "weekly milestones and checkpoints",
            "milestones and checkpoints",
            "weekly milestones",
        ],
        "Next Steps": [
            "next steps",
            "what to do next",
            "recommended next steps",
        ],
    }

    # Check whether each required section is present
    for section, alternatives in required_sections.items():
        if not any(
            alternative in normalized_roadmap
            for alternative in alternatives
        ):
            warnings.append(f"Missing section: {section}")

    # Detect common heading formats:
    # Week 1: Python Basics
    # ### Week 2 - Data Analysis
    # **Week 3: Practice**
    # 1. Week 1: Introduction
    week_pattern = re.compile(
        r"^[ \t]*"
        r"(?:#{1,6}[ \t]*)?"
        r"(?:\d+[.)][ \t]*)?"
        r"\**[ \t]*Week[ \t]+(\d+)\b",
        re.IGNORECASE | re.MULTILINE,
    )

    detected_numbers = [
        int(number)
        for number in week_pattern.findall(roadmap)
    ]

    unique_weeks = sorted(set(detected_numbers))
    expected_weeks = list(range(1, duration_weeks + 1))

    missing_weeks = sorted(
        set(expected_weeks) - set(unique_weeks)
    )

    if missing_weeks:
        warnings.append(
            f"Missing weekly headings for: {missing_weeks}. "
            f"Expected Week 1 through Week {duration_weeks}."
        )

    unexpected_weeks = sorted(
        set(unique_weeks) - set(expected_weeks)
    )

    if unexpected_weeks:
        warnings.append(
            f"Unexpected week numbers detected: {unexpected_weeks}."
        )

    # Check whether study-hour information appears
    if not re.search(
        r"\b(?:hours?|hrs?)\b",
        roadmap,
        re.IGNORECASE,
    ):
        warnings.append(
            "The roadmap does not clearly mention study-hour allocations."
        )

    # Validate requested study time
    if hours_per_week <= 0:
        warnings.append(
            "Study hours per week must be greater than zero."
        )

    return warnings


# Generate and validate a complete roadmap
def generate_roadmap(
    goal,
    current_skills,
    level,
    hours_per_week,
    duration_weeks,
    learning_style="Hands-on practice",
    learning_language="English",
    retrieved_context="",
    client=None,
):
    # Validate the learner's goal
    if not isinstance(goal, str) or not goal.strip():
        raise ValueError(
            "Please enter your career or learning goal."
        )

    if not isinstance(current_skills, str) or not current_skills.strip():
        current_skills = "No skills specified yet"

    if level not in ["Beginner", "Intermediate", "Advanced"]:
        raise ValueError(
            "Level must be Beginner, Intermediate, or Advanced."
        )

    if (
        isinstance(hours_per_week, bool)
        or not isinstance(hours_per_week, (int, float))
    ):
        raise ValueError("Study hours must be a number.")

    if not 1 <= hours_per_week <= 80:
        raise ValueError(
            "Study hours must be between 1 and 80 per week."
        )

    if (
        isinstance(duration_weeks, bool)
        or not isinstance(duration_weeks, int)
    ):
        raise ValueError(
            "Duration must be a whole number of weeks."
        )

    if not 1 <= duration_weeks <= 52:
        raise ValueError(
            "Duration must be between 1 and 52 weeks."
        )

    # Build the personalized roadmap prompt
    messages = build_roadmap_messages(
        goal=goal,
        current_skills=current_skills,
        level=level,
        hours_per_week=hours_per_week,
        duration_weeks=duration_weeks,
        learning_style=learning_style,
        learning_language=learning_language,
        retrieved_context=retrieved_context,
    )

    # Collect streamed text into one complete roadmap
    roadmap_parts = []

    for chunk in generate_response(
        messages=messages,
        stream=True,
        client=client,
    ):
        roadmap_parts.append(chunk)

    roadmap = "".join(roadmap_parts).strip()

    if not roadmap:
        raise RuntimeError(
            "The AI returned an empty roadmap. Please try again."
        )

    # Validate the generated content
    warnings = validate_roadmap(
        roadmap=roadmap,
        duration_weeks=duration_weeks,
        hours_per_week=hours_per_week,
    )

    return {
        "roadmap": roadmap,
        "warnings": warnings,
    }

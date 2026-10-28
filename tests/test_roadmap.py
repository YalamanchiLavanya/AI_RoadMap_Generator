
# tests/test_roadmap.py

import io
import json
from unittest.mock import MagicMock

import pytest

from roadmap_engine import (
    generate_roadmap,
    validate_roadmap,
    generate_response,
)
from progress import (
    create_progress,
    update_week_progress,
    get_progress_summary,
    export_progress,
    import_progress,
)
from rag_system import create_knowledge_base


# Sample roadmap used by tests
SAMPLE_ROADMAP = """
# Goal Overview
Become a Python Developer.

# Current Skill Assessment
Beginner with basic computer knowledge.

# Skill Gaps
Python fundamentals and practical programming.

# Week-by-Week Learning Plan
## Week 1: Python Basics
Study variables and data types for 5 hours.

## Week 2: Python Practice
Practice conditions and loops for 5 hours.

# Learning Resources
- Python documentation.

# Portfolio Project
Create a simple calculator.

# Weekly Milestones and Checkpoints
- Week 1: Write a simple program.
- Week 2: Complete the calculator.

# Next Steps
Continue practising Python.
"""


# ---------------------------------------------------------
# 1. ROADMAP VALIDATION TESTS
# ---------------------------------------------------------

def test_valid_roadmap_has_no_warnings():
    warnings = validate_roadmap(
        SAMPLE_ROADMAP,
        duration_weeks=2,
        hours_per_week=5,
    )

    assert warnings == []


def test_missing_roadmap_section_is_detected():
    incomplete_roadmap = """
    # Goal Overview
    Learn Python.
    """

    warnings = validate_roadmap(
        incomplete_roadmap,
        duration_weeks=2,
        hours_per_week=5,
    )

    assert any("Missing section" in warning for warning in warnings)


def test_incorrect_number_of_weeks_is_detected():
    warnings = validate_roadmap(
        SAMPLE_ROADMAP,
        duration_weeks=3,
        hours_per_week=5,
    )

    assert any("Expected weeks" in warning for warning in warnings)


# ---------------------------------------------------------
# 2. USER INPUT VALIDATION TESTS
# ---------------------------------------------------------

def test_empty_goal_is_rejected():
    with pytest.raises(ValueError, match="career or learning goal"):
        generate_roadmap(
            goal=" ",
            current_skills="Python",
            level="Beginner",
            hours_per_week=5,
            duration_weeks=2,
        )


def test_invalid_experience_level_is_rejected():
    with pytest.raises(ValueError, match="Level must be"):
        generate_roadmap(
            goal="Become a developer",
            current_skills="Python",
            level="Expert",
            hours_per_week=5,
            duration_weeks=2,
        )


def test_zero_study_hours_is_rejected():
    with pytest.raises(ValueError, match="between 1 and 80"):
        generate_roadmap(
            goal="Become a developer",
            current_skills="Python",
            level="Beginner",
            hours_per_week=0,
            duration_weeks=2,
        )


def test_invalid_duration_is_rejected():
    with pytest.raises(ValueError, match="between 1 and 52"):
        generate_roadmap(
            goal="Become a developer",
            current_skills="Python",
            level="Beginner",
            hours_per_week=5,
            duration_weeks=0,
        )


# ---------------------------------------------------------
# 3. PROGRESS TRACKING TESTS
# ---------------------------------------------------------

def test_create_progress():
    progress = create_progress(
        SAMPLE_ROADMAP,
        duration_weeks=2,
    )

    assert progress["duration_weeks"] == 2
    assert len(progress["weekly_progress"]) == 2
    assert progress["weekly_progress"][0]["completed"] is False


def test_update_week_progress():
    progress = create_progress(
        SAMPLE_ROADMAP,
        duration_weeks=2,
    )

    update_week_progress(
        progress,
        week_number=1,
        completed=True,
        notes="Finished Python basics.",
    )

    assert progress["weekly_progress"][0]["completed"] is True
    assert (
        progress["weekly_progress"][0]["notes"]
        == "Finished Python basics."
    )


def test_progress_summary():
    progress = create_progress(
        SAMPLE_ROADMAP,
        duration_weeks=2,
    )

    update_week_progress(progress, 1, True)

    summary = get_progress_summary(progress)

    assert summary["completed_weeks"] == 1
    assert summary["remaining_weeks"] == 1
    assert summary["completion_percentage"] == 50.0


def test_progress_export_and_import():
    progress = create_progress(
        SAMPLE_ROADMAP,
        duration_weeks=2,
    )

    update_week_progress(
        progress,
        week_number=1,
        completed=True,
        notes="Completed.",
    )

    exported = export_progress(progress)
    imported = import_progress(exported)

    assert imported["duration_weeks"] == 2
    assert imported["weekly_progress"][0]["completed"] is True
    assert imported["weekly_progress"][0]["notes"] == "Completed."


def test_invalid_progress_json_is_rejected():
    with pytest.raises(ValueError, match="valid JSON"):
        import_progress("{not valid json")


def test_invalid_week_number_is_rejected():
    progress = create_progress(
        SAMPLE_ROADMAP,
        duration_weeks=2,
    )

    with pytest.raises(ValueError, match="outside the roadmap"):
        update_week_progress(progress, 3, True)


# ---------------------------------------------------------
# 4. GEMINI API FAILURE TEST
# ---------------------------------------------------------

def test_api_failure_does_not_retry_after_text_is_emitted():
    # Mock the Gemini client
    client = MagicMock()

    def broken_stream(**kwargs):
        # First, return a chunk successfully
        yield MagicMock(text="Week 1: Python basics")

        # Then simulate a network interruption
        raise ConnectionError("Simulated connection failure")

    client.models.generate_content_stream.side_effect = broken_stream

    messages = [
        {
            "role": "user",
            "content": "Create a Python roadmap.",
        }
    ]

    response_parts = []

    with pytest.raises(RuntimeError, match="stream was interrupted"):
        for chunk in generate_response(
            messages,
            stream=True,
            client=client,
            max_retries=2,
        ):
            response_parts.append(chunk)

    # The first chunk should appear only once
    assert response_parts == ["Week 1: Python basics"]

    # The interrupted stream must not be restarted
    assert client.models.generate_content_stream.call_count == 1


# ---------------------------------------------------------
# 5. PDF KNOWLEDGE BASE TESTS
# ---------------------------------------------------------

def test_empty_knowledge_base_returns_empty_context():
    knowledge_base = create_knowledge_base()

    assert knowledge_base.search("Python basics") == ""
    assert knowledge_base.is_ready() is False


def test_clear_pdf_index_removes_old_data():
    knowledge_base = create_knowledge_base()

    # Add a lightweight fake index and metadata
    knowledge_base.index = MagicMock()
    knowledge_base.chunks = [
        {
            "text": "Old PDF content",
            "page": 1,
            "filename": "old.pdf",
        }
    ]
    knowledge_base.filename = "old.pdf"

    knowledge_base.clear()

    assert knowledge_base.index is None
    assert knowledge_base.chunks == []
    assert knowledge_base.filename is None
    assert knowledge_base.is_ready() is False


# ---------------------------------------------------------
# 6. ROADMAP REVISION CONSISTENCY TEST
# ---------------------------------------------------------

def test_revised_roadmap_can_replace_saved_roadmap():
    progress = create_progress(
        SAMPLE_ROADMAP,
        duration_weeks=2,
    )

    revised_roadmap = SAMPLE_ROADMAP.replace(
        "Create a simple calculator.",
        "Create a weather application.",
    )

    # Simulate explicitly applying a proposed revision
    saved_roadmap = revised_roadmap
    progress = create_progress(saved_roadmap, duration_weeks=2)

    assert "weather application" in saved_roadmap
    assert progress["roadmap"] == saved_roadmap
    assert progress["weekly_progress"][0]["completed"] is False


# ---------------------------------------------------------
# 7. RESOURCE LINK PRESENCE TEST
# ---------------------------------------------------------

def test_roadmap_contains_learning_resources_section():
    warnings = validate_roadmap(
        SAMPLE_ROADMAP,
        duration_weeks=2,
        hours_per_week=5,
    )

    assert not any(
        "Missing section: Learning Resources" in warning
        for warning in warnings
    )

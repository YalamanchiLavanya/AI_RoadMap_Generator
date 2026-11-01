"""Shared test helpers: a fake Gemini client, plan/PDF factories, a fake embedder.

The fake client mimics the two SDK calls the app uses
(``client.models.generate_content_stream`` and ``client.models.generate_content``),
so the real retry/streaming code path is exercised without a network or API key.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import sys
import textwrap
from io import BytesIO

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import LearnerProfile, Settings  # noqa: E402

TEST_SETTINGS = Settings(api_key="test-key", model="test-model", max_output_tokens=1000)


# --------------------------------------------------------------------------
# Fake Gemini client
# --------------------------------------------------------------------------
class FakeChunk:
    def __init__(self, text):
        self.text = text


class FakeResponse:
    def __init__(self, text):
        self.text = text


class FakeModels:
    """Each script is a list of text pieces and/or exceptions to raise mid-stream.

    A script that is itself an exception is raised as soon as the call is made.
    """

    def __init__(self, scripts):
        self.scripts = list(scripts)
        self.calls: list[dict] = []

    def _next_script(self, model, contents, config):
        self.calls.append({"model": model, "contents": contents, "config": config})
        if not self.scripts:
            raise AssertionError("The fake client ran out of scripted responses.")
        script = self.scripts.pop(0)
        if isinstance(script, BaseException):
            raise script
        return script

    def generate_content_stream(self, *, model, contents, config):
        script = self._next_script(model, contents, config)

        def iterate():
            for item in script:
                if isinstance(item, BaseException):
                    raise item
                yield FakeChunk(item)

        return iterate()

    def generate_content(self, *, model, contents, config):
        script = self._next_script(model, contents, config)
        text = ""
        for item in script:
            if isinstance(item, BaseException):
                raise item
            text += item
        return FakeResponse(text)


class FakeClient:
    def __init__(self, scripts):
        self.models = FakeModels(scripts)

    @property
    def calls(self):
        return self.models.calls


class Sleeper:
    """Records back-off delays instead of sleeping."""

    def __init__(self):
        self.delays: list[float] = []

    def __call__(self, seconds):
        self.delays.append(seconds)


def split_text(text: str, pieces: int = 3) -> list[str]:
    size = max(1, len(text) // pieces)
    return [text[i : i + size] for i in range(0, len(text), size)]


def plan_script(plan: dict) -> list[str]:
    """A scripted streaming response that delivers `plan` as JSON in pieces."""
    return split_text(json.dumps(plan))


# --------------------------------------------------------------------------
# Plan factory
# --------------------------------------------------------------------------
def make_profile(**overrides) -> LearnerProfile:
    values = {
        "goal": "Learn SQL for reporting",
        "current_skills": "Excel basics",
        "level": "Beginner",
        "hours_per_week": 8,
        "duration_weeks": 4,
    }
    values.update(overrides)
    return LearnerProfile(**values)


def make_plan(weeks: int = 4, hours: int = 8, *, realistic: bool = True, per_week: float | None = None) -> dict:
    """A valid plan: `weeks` weeks, each using `per_week` (default: all) of `hours`."""
    total = float(per_week if per_week is not None else hours)
    half = round(total / 2, 2)
    return {
        "feasibility": {
            "realistic": realistic,
            "summary": "The plan fits the time available." if realistic else "Too little time for the full goal.",
            "achievable_outcome": "" if realistic else "Write basic SQL queries for reports.",
        },
        "overview": "Learn SQL step by step.",
        "skill_assessment": "Knows spreadsheets; new to databases.",
        "skill_gaps": ["SELECT queries", "Joins"],
        "constraints": {"hours_per_week": hours, "duration_weeks": weeks},
        "weeks": [
            {
                "week": n,
                "title": f"Topic {n}",
                "focus": f"Focus {n}",
                "activities": [
                    {"task": f"Study topic {n}", "type": "learn", "hours": half},
                    {"task": f"Practice topic {n}", "type": "practice", "hours": round(total - half, 2)},
                ],
                "milestone": f"Finish exercises for topic {n}",
                "resources": [
                    {"title": f"Resource {n}", "provider": "Example Org", "url": f"https://example.com/w{n}"}
                ],
                "source_pages": [],
            }
            for n in range(1, weeks + 1)
        ],
        "portfolio_project": {
            "title": "Sales report",
            "description": "Query a sample database and report three findings.",
            "deliverables": ["SQL file", "Summary"],
        },
        "next_steps": ["Learn window functions"],
    }


def clone(plan: dict) -> dict:
    return copy.deepcopy(plan)


# --------------------------------------------------------------------------
# PDF factory and fake embedder
# --------------------------------------------------------------------------
def make_pdf(pages: list[str]) -> bytes:
    """Build a real PDF with one page per string ("" gives a page with no text)."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    for text in pages:
        y = 800
        for line in textwrap.wrap(text, 85) if text else []:
            pdf.drawString(50, y, line)
            y -= 14
        pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def fake_embed(texts: list[str]) -> np.ndarray:
    """Deterministic bag-of-words embedding: shared words give similar vectors."""
    vectors = np.zeros((len(texts), 256), dtype="float32")
    for row, text in enumerate(texts):
        for word in re.findall(r"[a-z0-9]+", text.lower()):
            vectors[row, int(hashlib.md5(word.encode()).hexdigest(), 16) % 256] += 1.0
    return vectors

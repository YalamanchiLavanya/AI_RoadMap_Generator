# AI Learning Roadmap Generator

A Streamlit app that turns a learner's goal, skills, level, weekly hours and duration into a
**validated** week-by-week roadmap, with a coach chat, optional PDF knowledge (RAG), verified
resource links, and progress tracking that feeds back into the coach.

## What changed after the project feedback

| # | Feedback | What the app does now | Where |
|---|---|---|---|
| 1 | Retry during streaming repeated text | Automatic retry only **before** any text is emitted. If a stream breaks after text appeared, `StreamInterruptedError` carries the partial text; roadmap/revision calls discard it and restart cleanly, chat shows it as unsaved and offers **Retry**. | `roadmap_engine.generate_response`, `collect_text` |
| 2 | Chat revisions did not update the roadmap | **Revise the roadmap** drafts a full revised plan; nothing changes until **Apply revised roadmap**. Display, download, tracker and export all read one stored plan. | `roadmap_engine.revise_roadmap`, `progress.apply_pending_revision`, Coach tab |
| 3 | Limits depended on prompting | The model returns structured JSON. The app checks week count, per-week hours, required sections, milestones and feasibility before showing it. Small hour overruns are scaled down (and reported); bigger problems get one repair request; a plan that still fails is not shown. Unrealistic goals produce a visible "reality check" with what *is* achievable. | `roadmap_engine.validate_plan`, `assess_time_budget` |
| 4 | PDF handled inconsistently | The indexed PDF is used in roadmap generation, coach chat **and** revisions. Chunks keep page numbers; answers cite pages. Removing or replacing the file clears the old index (tracked by file hash). | `rag_system.py` |
| 5 | Progress not connected | Tasks are built from weekly activities + milestones; completion is sent to the coach; completed tasks survive a revision; progress can be exported/restored as JSON. | `progress.py` |
| 6 | Testing evidence | 100 automated tests (fake Gemini client, real PDFs, local HTTP server) plus a documented live-test matrix. Links are verified before being called curated. | `tests/`, `docs/`, `link_checker.py` |

## Project structure

```
app.py              Streamlit interface only
config.py           settings, limits, LearnerProfile, client creation
prompts.py          roadmap, revision and coach prompts
roadmap_engine.py   generation, streaming/retry, parsing, validation, revision, Markdown
rag_system.py       PDF extraction, page-aware chunking, FAISS/NumPy retrieval, replace/remove rules
progress.py         tasks, completion, export/import, plan state transitions
link_checker.py     verifies recommended URLs (refuses private/local addresses)
tests/              unit tests (unittest-compatible; pytest also works)
docs/               TEST_EVIDENCE.md, DEMO_SCRIPT.md
```

## Setup

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
cp .env.example .env                                   # then put your own key in .env
python -m streamlit run app.py
```

On Streamlit Community Cloud, add `GEMINI_API_KEY` (and optionally `GEMINI_MODEL`) under
**App settings > Secrets** instead of using `.env`.

## Running the tests

```bash
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -t . -v      # or: pytest
```

The tests need no API key and no internet. They do **not** call real Gemini, so they prove the
app's logic, not the quality of live model output - see `docs/TEST_EVIDENCE.md` for what is and
is not covered, and for the live-test matrix to fill in.

## Notes and limits

* Progress lives in the browser session. Use **Export progress** to continue later.
* Link checks show what answered when checked; sites that block bots appear as "could not verify".
* The "total hours look too small" rule is a rough rule of thumb used to alert the model and the
  learner, not a guarantee. Check `assess_time_budget` in `roadmap_engine.py` to tune it.
* Never commit `.env`. If a key was ever shared or committed, rotate it.

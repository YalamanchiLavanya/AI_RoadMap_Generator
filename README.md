# AI Learning Roadmap Generator

A Streamlit application that transforms a learner's career goal, current skills, experience level, available weekly study hours, and learning duration into a **validated, personalized week-by-week learning roadmap**.

The application includes an AI Roadmap Coach, optional PDF-based knowledge retrieval (RAG), resource URL reachability checking, and progress tracking connected to the generated roadmap.

## Features

- **Personalized Roadmaps:** Generate learning plans based on career goals, existing skills, experience level, available study hours, and learning duration.
- **Structured Roadmap Validation:** Validate the number of weeks, weekly study hours, activities, milestones, and required sections before displaying a roadmap.
- **Feasibility Checks:** Identify potentially unrealistic learning goals and suggest achievable alternatives within the available study time.
- **Streaming and Retry Handling:** Retry generation only before text has been emitted. Handle interrupted streams without silently saving duplicated roadmap content.
- **Roadmap Coach:** Ask questions about the roadmap and draft revisions. Changes are applied to the stored roadmap only after confirmation.
- **PDF-Based RAG:** Upload learning materials and retrieve relevant passages using embeddings and FAISS/NumPy retrieval, including page references.
- **PDF Replacement and Removal:** Clear the previous document index when a PDF is replaced or removed.
- **PDF Citation Validation:** Validate document citations against retrieved PDF passages and remove unsupported references.
- **Resource Link Checking:** Check URL reachability and distinguish reachable, broken, invalid, and unverified links.
- **Progress Tracking:** Track completed activities and milestones, preserve completed tasks during revisions, and export/import progress as JSON.
- **Multilingual Support:** Generate roadmaps in English, Telugu + English, and Hindi + English.
- **Roadmap Downloads:** Download the generated roadmap in Markdown format.

## What Changed After Project Feedback

| # | Feedback | Improvement | Location |
|---|---|---|---|
| 1 | Interrupted streaming could repeat text | Retry only before text is emitted and handle interrupted output without silently saving duplicate plans. | `roadmap_engine.py` |
| 2 | Coach revisions did not update the roadmap | Added a draft-and-apply workflow. Applying a revision updates the stored roadmap and connected progress information. | `roadmap_engine.py`, `progress.py`, Coach tab |
| 3 | Roadmap limits depended on prompting | Added structured JSON generation and validation for weeks, hours, activities, milestones, and required sections. | `roadmap_engine.py` |
| 4 | PDF handling was inconsistent | Use indexed PDF content during generation, chat, and revisions. Clear the previous index when replacing or removing a PDF. | `rag_system.py` |
| 5 | Progress was not connected to the coach | Generate progress tasks from roadmap activities and milestones. Share completion information with the coach and support progress export/import. | `progress.py` |
| 6 | Testing evidence needed improvement | Added automated pytest tests and a live evaluation matrix for Gemini generation, RAG, progress, revisions, and Streamlit UI behavior. | `tests/`, `docs/` |
| 7 | Resource verification claims were too broad | Clarified that URL checking verifies HTTP reachability only. Resource relevance, freshness, beginner-friendliness, and language suitability require manual assessment. | `link_checker.py`, `docs/TEST_EVIDENCE.md` |
| 8 | PDF replacement could leave outdated chat context | Filter document-derived chat history against the currently active PDF. | `app.py` |
| 9 | PDF citations needed validation | Check citations against retrieved document passages and remove unsupported references. | `app.py` |
| 10 | Active roadmap settings needed visibility | Display the active plan's study hours, duration, and version, including in progress information and roadmap downloads. | `app.py`, `progress.py` |

## Project Structure

```text
AI_Roadmap_Generator/
│
├── app.py                  # Streamlit user interface
├── config.py               # Settings, limits, learner profile, API client
├── prompts.py              # System, roadmap, revision, and coach prompts
├── roadmap_engine.py       # Generation, streaming, validation, revision
├── rag_system.py           # PDF extraction, embeddings, retrieval
├── progress.py             # Progress tasks, completion, export/import
├── link_checker.py         # URL reachability and safety checks
│
├── tests/                  # Automated pytest test suite
│   ├── helpers.py
│   │── test_coach_context.py
│   ├── test_links_and_markdown.py
│   ├── test_pdf_replacement_flow.py
│   ├── test_progress_and_revision.py
│   ├── test_rag_system.py
│   ├── test_streaming.py
│   └── test_validation.py
│
├── docs/
│   ├── TEST_EVIDENCE.md    # Automated and live evaluation evidence
│   ├── DEMO_SCRIPT.md      # Project demonstration instructions
│   └── evidence/           # Test screenshots
│
├── .streamlit/
│   └── config.toml
│
├── .env.example
├── requirements.txt        # Application dependencies
├── requirements-dev.txt    # Development and testing dependencies
├── requirements-lock.txt   # Recorded package versions
├── .gitignore
└── README.md
```

The structure highlights the main project files. Additional files may be present in the repository.

## Requirements

- Python 3.12 or a compatible version.
- A valid Gemini API key.
- Internet connection for live Gemini requests and external resource checking.
- Development dependencies for running automated tests.

## Setup and Installation

### 1. Clone the repository
```bash
git clone https://github.com/YalamanchiLavanya/AI_RoadMap_Generator.git
cd AI_RoadMap_Generator
```
### 2. Create and activate a virtual environment

**Windows PowerShell:**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS/Linux:**

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install application dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Configure the Gemini API key

Copy the example environment file.

**Windows PowerShell:**

```powershell
Copy-Item .env.example .env
```

**macOS/Linux:**

```bash
cp .env.example .env
```

Add your Gemini API key to the `.env` file:

```env
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash
```

Use your own valid Gemini API key.

**Security:** Never commit `.env` or any file containing API credentials to GitHub.

### 5. Run the application

```bash
python -m streamlit run app.py
```

The application will open in your browser.

## Running the Automated Tests

The project uses **pytest** as its automated test runner.

### 1. Install development dependencies

```bash
python -m pip install -r requirements-dev.txt
```

### 2. Collect tests without executing them

```bash
python -m pytest --collect-only -q
```

### 3. Run the complete automated test suite

```bash
python -m pytest -v
```

### Dependency lock file

`requirements-lock.txt` records the package versions captured from the local Python environment.

To install the recorded package versions:

```bash
python -m pip install -r requirements-lock.txt
```

The lock file should be used with a compatible Python environment. Its contents reflect the environment from which it was generated.

### Latest Previously Recorded Automated Test Results

| Metric | Result |
|---|---:|
| Python version | 3.12.10 |
| Pytest version | 9.2.0 |
| Tests collected | 110 |
| Tests passed | 110 |
| Tests failed | 0 |
| Subtests passed | 23 |
| Execution time | 4.11 seconds |

These are previously recorded local test results, not a claim that the latest changes have been independently verified from a clean Git checkout.

Automated tests use controlled test data, mocked services, and local test resources. They do not prove the quality of live Gemini responses or replace testing with the actual Streamlit interface and configured embedding model.

See `docs/TEST_EVIDENCE.md` for detailed test cases, actual observations, screenshots, and the L01–L13 live evaluation matrix.

## Live Evaluation

The live evaluation matrix covers:

- Gemini roadmap generation.
- Beginner and intermediate learner personalization.
- Weekly study-hour and duration validation.
- Streaming and interrupted generation.
- Roadmap revision and apply workflow.
- PDF upload, indexing, replacement, and removal.
- PDF-based chat history and citation validation.
- Progress tracking, export, and import.
- External resource URL reachability and manual quality assessment.
- Streamlit interface and navigation.
- API configuration and error handling.
- English, Telugu + English, and Hindi + English output.
- Active roadmap settings and revision updates.

Record actual observations and screenshots for each test in `docs/TEST_EVIDENCE.md`.

A test should be marked **Passed** only after it has been executed and its expected behavior verified. Tests that have not been performed should remain Pending.

## Resource Verification Limitations

The link checker checks whether a URL responds to an HTTP request.

| Status | Meaning |
|---|---|
| Reachable | The URL returned a successful HTTP response. |
| Broken | The URL returned a clear client error. |
| Unverified | The URL could not be checked reliably. |
| Invalid | The URL is not a valid supported HTTP/HTTPS URL. |
| No link | No URL was provided. |

A reachable URL does not establish that the material is relevant, current, beginner-friendly, or suitable for the requested language.

These characteristics must be assessed manually during live evaluation.

## Deployment

The application can be deployed using Streamlit Community Cloud.

1. Push the project to GitHub.
2. Open Streamlit Community Cloud.
3. Connect your GitHub repository.
4. Select `app.py` as the application entry point.
5. Add the following secrets in the application's settings:

```toml
GEMINI_API_KEY = "your_gemini_api_key"
GEMINI_MODEL = "gemini-2.5-flash"
```

Do not upload your local `.env` file or expose API credentials.

## Notes and Limitations

- Progress is maintained in the current browser session. Use **Export Progress** to save progress for later restoration.
- Live Gemini generation requires a valid API key and internet connection.
- PDF retrieval requires the configured embedding model and vector retrieval dependencies.
- PDF citations depend on the retrieved document passages and available page references.
- External resource checking confirms reachability, not content quality.
- Feasibility warnings are guidance based on available learning time, not guarantees of completing a goal.
- Resource availability and external website behavior can change over time.
- Never commit `.env` or other files containing API keys.

## Documentation

- `docs/TEST_EVIDENCE.md` – Automated and live testing evidence.
- `docs/DEMO_SCRIPT.md` – Project demonstration instructions.
- `tests/` – Automated test cases.

## Author

**Lavanya Yalamanchi**

AI Learning Roadmap Generator – Generative AI Project

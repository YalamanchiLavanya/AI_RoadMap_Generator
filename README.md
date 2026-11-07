# AI Learning Roadmap Generator

A Streamlit application that turns a learner's career goal, current skills, experience level, weekly study hours, and learning duration into a **validated, personalized week-by-week learning roadmap**.

The application includes an AI Roadmap Coach, optional PDF-based knowledge retrieval (RAG), resource URL reachability checking, and progress tracking connected to the roadmap.

## Features

- **Personalized Roadmaps:** Generate learning plans based on career goals, existing skills, experience level, available study hours, and duration.
- **Structured Roadmap Validation:** Validate week count, weekly hours, activities, milestones, and required sections before displaying a roadmap.
- **Feasibility Checks:** Identify unrealistic learning goals and provide achievable alternatives within the available time.
- **Streaming and Retry Handling:** Avoid duplicate saved content when generation is interrupted. Retry automatically only before any text has been emitted.
- **Roadmap Coach:** Ask questions about the roadmap and draft revisions. Changes are applied only after confirmation.
- **PDF-Based RAG:** Upload learning materials and retrieve relevant passages using embeddings and FAISS/NumPy retrieval, with page references.
- **PDF Replacement and Removal:** Clear the previous document index when a PDF is replaced or removed.
- **Resource Link Checking:** Check URL reachability and distinguish reachable, broken, invalid, and unverified links.
- **Progress Tracking:** Track completed activities and milestones, preserve completed tasks during revisions, and export/import progress as JSON.
- **Multilingual Support:** Generate roadmaps in English, Telugu + English, and Hindi + English.

## What Changed After Project Feedback

| # | Feedback | Improvement | Location |
|---|---|---|---|
| 1 | Interrupted streaming could repeat text | Retry only before text is emitted. Interrupted streams carry partial output and are handled without silently saving duplicated plans. | `roadmap_engine.py` |
| 2 | Coach revisions did not update the roadmap | Added a draft-and-apply workflow. Applying a revision updates the stored roadmap, downloads, and progress tracker together. | `roadmap_engine.py`, `progress.py`, Coach tab |
| 3 | Roadmap limits depended on prompting | Added structured JSON generation and validation for weeks, hours, activities, milestones, and required sections. | `roadmap_engine.py` |
| 4 | PDF handling was inconsistent | Use indexed PDF content during generation, chat, and revisions. Preserve page references and clear the previous index when replacing or removing a PDF. | `rag_system.py` |
| 5 | Progress was not connected to the coach | Generate progress tasks from roadmap activities and milestones. Send completion information to the coach and support progress export/import. | `progress.py` |
| 6 | Testing evidence needed improvement | Added automated tests and a live evaluation matrix covering real Gemini generation, RAG, progress, revisions, and Streamlit UI behavior. | `tests/`, `docs/` |
| 7 | Resource verification claims were too broad | URL checking reports HTTP reachability only. Resource relevance, freshness, beginner-friendliness, and language suitability require separate manual assessment. | `link_checker.py`, `docs/TEST_EVIDENCE.md` |

## Project Structure

```text
AI_Learning_Roadmap_Generator/
│
├── app.py              # Streamlit user interface
├── config.py           # Settings, limits, learner profile, API client
├── prompts.py          # System, roadmap, revision, and coach prompts
├── roadmap_engine.py   # Generation, streaming, validation, revision
├── rag_system.py       # PDF extraction, embeddings, FAISS/NumPy retrieval
├── progress.py         # Progress tasks, completion, export/import
├── link_checker.py     # URL reachability and safety checks
│
├── tests/              # Automated pytest test suite
│
├── docs/
│   ├── TEST_EVIDENCE.md
│   ├── DEMO_SCRIPT.md
│   └── evidence/       # Actual test screenshots
│
├── .streamlit/
│   └── config.toml
│
├── .env.example
├── requirements.txt
├── requirements-dev.txt
├── .gitignore
└── README.md
```

*The structure above highlights the main project files. Additional files may be present in the repository.*

## Requirements

- Python 3.12 or compatible version
- Gemini API key
- Internet connection for live Gemini requests and external resource checking
- Development dependencies for running automated tests

## Setup and Installation

### 1. Clone the repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd AI_Learning_Roadmap_Generator
```

Replace `YOUR_GITHUB_REPOSITORY_URL` with your actual repository URL.

### 2. Create a virtual environment

**Windows PowerShell:**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
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

Copy the example environment file:

**Windows PowerShell:**

```powershell
Copy-Item .env.example .env
```

**macOS/Linux:**

```bash
cp .env.example .env
```

Add your API key to `.env`:

```env
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash
```

Use your own valid Gemini API key. Never commit `.env` to GitHub.

### 5. Run the application

```bash
python -m streamlit run app.py
```

The application will open in your browser.

## Running the Tests

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

### Latest Recorded Automated Test Results

| Metric | Result |
|---|---:|
| Python version | 3.12.10 |
| Pytest version | 9.2.0 |
| Tests collected | 100 |
| Tests passed | 100 |
| Tests failed | 0 |
| Subtests passed | 23 |
| Execution time | 4.78 seconds |

These are the previously recorded local test results. They must be re-confirmed from a clean Git checkout before being treated as final submission evidence.

Automated tests use controlled test data, mocked services, and local test resources. They do not prove the quality of live Gemini responses or replace testing with the actual Streamlit interface and configured embedding model.

See `docs/TEST_EVIDENCE.md` for detailed test cases, actual observations, screenshots, and the L01–L13 live evaluation matrix.

Pytest is a required development dependency for running the automated test suite.

## Live Evaluation

The live evaluation matrix covers:

- Gemini roadmap generation.
- Beginner and intermediate learner personalization.
- Weekly study-hour and duration validation.
- Streaming and interrupted generation.
- Roadmap revision and apply workflow.
- PDF upload, indexing, replacement, and removal.
- Progress tracking, export, and import.
- External resource URL reachability and manual quality assessment.
- Streamlit interface and navigation.
- API configuration and error handling.
- English, Telugu + English, and Hindi + English output.

Record actual observations and screenshots for each test in `docs/TEST_EVIDENCE.md`.

A test should be marked Passed only after it has been executed and its expected behavior verified.

## Resource Verification Limitations

The link checker checks whether a URL responds to an HTTP request.

- **Reachable:** The URL returned a successful HTTP response.
- **Broken:** The URL returned a clear client error.
- **Unverified:** The URL could not be checked reliably.
- **Invalid:** The URL is not a valid supported HTTP/HTTPS URL.
- **No link:** No URL was provided.

A reachable URL does not establish that the material is relevant, current, beginner-friendly, or suitable for the requested language.

These characteristics must be assessed manually during live evaluation.

## Deployment

The application can be deployed using Streamlit Community Cloud.

1. Push the project to GitHub.
2. Connect the GitHub repository to Streamlit Community Cloud.
3. Select `app.py` as the application entry point.
4. Add the following secrets under the app settings:

```toml
GEMINI_API_KEY = "your_gemini_api_key"
GEMINI_MODEL = "gemini-2.5-flash"
```

Do not upload your local `.env` file or expose API credentials.

## Notes and Limitations

- Progress is maintained in the current browser session. Use **Export Progress** to save progress for later restoration.
- Live Gemini generation requires a valid API key and internet connection.
- PDF retrieval requires the configured embedding model and vector retrieval dependencies.
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
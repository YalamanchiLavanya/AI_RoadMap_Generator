# AI Learning Roadmap Generator

An AI-powered application that creates personalized, week-by-week learning roadmaps based on a learner's career goal, current skills, experience level, available study hours, and preferred learning style.

The application uses Google's Gemini API to generate learning plans and supports PDF-based retrieval, interactive roadmap coaching, progress tracking, and downloadable roadmaps.

## Features

- **Personalized Roadmaps:** Generate structured weekly learning plans for different career goals.
- **AI Roadmap Coach:** Ask questions, clarify concepts, and request roadmap revisions.
- **PDF-Based RAG:** Upload reference PDFs and retrieve relevant information using embeddings and FAISS.
- **Progress Tracker:** Mark weekly milestones as completed and record notes.
- **Progress Import and Export:** Save and restore progress using JSON files.
- **Streaming Responses:** Display AI-generated responses as they arrive.
- **Prompt Engineering:** Use system instructions, few-shot examples, and contextual information.
- **Input Validation:** Validate learning goals, experience levels, study hours, and roadmap duration.
- **Automated Tests:** Use pytest to check core functionality and error handling.

## Technologies Used

- Python
- Streamlit
- Google Gemini API (`google-genai`)
- Sentence Transformers
- FAISS
- PyPDF
- NumPy
- pytest

## Project Structure

```text
AI_RoadMap_Generator/
├── app.py
├── config.py
├── prompts.py
├── roadmap_engine.py
├── rag_system.py
├── progress.py
├── requirements.txt
├── .env
├── .env.example
├── .gitignore
├── README.md
└── tests/
    └── test_roadmap.py
```

## Prerequisites

- Python 3.10 or later
- Internet connection
- A Gemini API key
- Basic familiarity with Python and the command line

## Installation

### 1. Open the project folder

```powershell
cd "C:\Users\User\OneDrive\Desktop\AI_RoadMap_Generator"
```

### 2. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 3. Configure the API key

Create a `.env` file in the project root directory.

Add the following settings:

```env
GEMINI_API_KEY=your_actual_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash
```

Replace the example API key with your own key. Keep `.env` private and never upload it to GitHub.

## Run the Application

Start the Streamlit application:

```powershell
python -m streamlit run app.py
```

Streamlit will display a local URL in the terminal. Open that URL in your browser.

## How to Use

1. Enter your career or learning goal.
2. Describe your current skills and select your experience level.
3. Choose your weekly study hours and roadmap duration.
4. Select your preferred learning style and language.
5. Generate your personalized roadmap.
6. Optionally upload a PDF to provide additional reference material.
7. Use the Roadmap Coach to ask questions or request changes.
8. Apply a proposed roadmap revision after reviewing it.
9. Track weekly milestones in the Progress Tracker.
10. Export your roadmap or save your progress as JSON.

## Run Automated Tests

Run the test suite with:

```powershell
python -m pytest tests/test_roadmap.py -v
```

The tests cover roadmap validation, input validation, progress tracking, API streaming failure handling, PDF-index clearing, and revision-related behavior.

## Project Architecture

- **`app.py`:** Streamlit user interface and session management.
- **`config.py`:** Gemini client configuration and environment settings.
- **`prompts.py`:** System instructions, few-shot examples, and roadmap prompts.
- **`roadmap_engine.py`:** AI response generation and roadmap validation.
- **`rag_system.py`:** PDF text extraction, embeddings, and FAISS similarity search.
- **`progress.py`:** Milestone tracking and JSON import/export.
- **`tests/test_roadmap.py`:** Automated tests for core functions.

## Limitations

- Roadmap quality depends on the AI model's output and the learner's inputs.
- Generated resource links should be checked before use.
- Scanned PDFs may require OCR to extract their text.
- Progress is stored in the active Streamlit session unless additional persistent storage is implemented.
- Structural validation does not guarantee that every weekly activity fits the available study hours.
- PDF retrieval provides relevant text excerpts but does not guarantee that every answer is fully supported by the uploaded document.

## Future Improvements

- Add persistent user accounts and database-backed progress.
- Improve validation of weekly time allocations and milestone quality.
- Add more comprehensive integration tests.
- Support OCR for scanned PDFs.
- Add charts showing learning progress and completed milestones.
- Improve roadmap revision detection and comparison.

## Author
Yalamanchi Lavanya
Developed as a Python and Generative AI project to help learners plan their career development through personalized learning roadmaps.
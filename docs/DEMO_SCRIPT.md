# AI Learning Roadmap Generator – Demo Script

**Duration:** 6–7 minutes  
**Purpose:** Demonstrate personalized roadmap generation, PDF-based RAG, roadmap coaching, revision workflow, progress tracking, resource verification, and error handling.

## Preparation Before Recording

Make sure you have:

- A working Gemini API key configured in `.env` or Streamlit secrets.
- A small PDF syllabus with at least 3 pages.
- A second, different PDF for testing document replacement.
- A stable internet connection.
- The application running locally or on Streamlit Cloud.
- A few tasks ready to mark as completed during the demo.

**Important:** Use your actual observations during the recording. Do not demonstrate a feature as successful unless you have tested it.

## Demo Timeline (6–7 Minutes)

| Time | Action | What to Say / Show |
|---|---|---|
| 0:00–0:30 | Open the application | Introduce the project: "The AI Learning Roadmap Generator converts a learner's career goal into a structured, validated weekly learning plan with milestones, verified resources, and progress tracking." Briefly introduce the application modules. |
| 0:30–1:30 | Generate a roadmap without a PDF | Enter Goal: **Become a Data Analyst**. Select Beginner level, enter 8 hours per week and 8 weeks, and leave the PDF option disabled. Click Generate Roadmap. Show the streaming progress. Explain that the application checks whether the available 64 hours are realistic for the selected goal. Point out the reality-check message and achievable outcome. |
| 1:30–2:00 | Review the generated roadmap | Scroll through the roadmap. Show the weekly learning tables, estimated hours, activities, and milestones. Point out the plan validation summary, including the number of weeks and the busiest week's hours. Open **Notes from the plan check**. |
| 2:00–2:30 | Demonstrate learning resources | Show the resources table. Explain that only verified links are presented as clickable verified resources. Show how unchecked or inaccessible links are labelled appropriately, such as "Could not verify" or a suggestion to search for the exact resource title. Open one verified link. |
| 2:30–3:15 | Generate a roadmap using a PDF | Upload the first syllabus PDF in the sidebar. Click **Index this PDF**, enable PDF usage for generation, and generate a roadmap. Explain: "The application extracts text from the uploaded PDF, creates searchable embeddings, retrieves relevant content, and uses it to improve the roadmap." Show document references with filenames and page numbers, if generated. |
| 3:15–3:45 | Demonstrate the Roadmap Coach | Open the Coach tab. Ask a question about prerequisites or a topic covered in the uploaded syllabus. Show the answer and its document citations. Open the Sources section to demonstrate the retrieved PDF references. |
| 3:45–4:45 | Revise and apply the roadmap | Open the roadmap revision workflow. Enter: **"I can only study 5 hours a week from now on."** Draft the revision. Show the proposed changes and preview. Explain that drafting does not immediately change the active roadmap. Click **Apply revised roadmap**. Return to the Roadmap tab and show the updated plan. Demonstrate that the download and progress tracker reflect the revised roadmap. |
| 4:45–5:45 | Demonstrate progress tracking | Open the Progress Tracker tab. Mark a few learning tasks as completed. Show the progress statistics and remaining tasks. Return to the Coach and ask: **"Am I on track?"** Explain that the coach receives the learner's current progress information. Export the progress data, refresh the application, and import the exported file to demonstrate restoration. |
| 5:45–6:30 | Demonstrate PDF replacement and removal | Replace the first PDF with the second, different PDF. Show that the previous document index is cleared and the new document is indexed. Ask a question related to the second PDF. Verify that the answer uses the new document rather than the old one. Remove the uploaded PDF and demonstrate that the document index and old document context are cleared. |
| 6:30–6:45 | Demonstrate failure handling (optional) | If practical, demonstrate an API or network failure. Explain how the application handles errors with a user-friendly message. Show retry behaviour only if it is available and successfully tested. |
| 6:45–7:00 | Show automated tests | Open the terminal and run `python -m pytest -v`. Show the final test summary: **110 passed, 23 subtests passed, 0 failed**. Open `docs/TEST_EVIDENCE.md` and briefly explain that automated and manual testing evidence is maintained there. |

## Key Features to Highlight

1. **Personalized learning plans:** Uses the learner's goal, current skills, experience level, available weekly hours, duration, and preferences.
2. **Roadmap validation:** Checks the generated roadmap structure, week count, activities, milestones, and time limits.
3. **Feasibility checking:** Identifies unrealistic learning goals and communicates achievable outcomes.
4. **Streaming and retry handling:** Handles interrupted or empty model responses without duplicating roadmap content.
5. **PDF-based RAG:** Extracts PDF content, creates embeddings, retrieves relevant passages, and uses them as additional context.
6. **Roadmap Coach:** Answers learner questions using the active roadmap, progress information, and relevant PDF context.
7. **Citation validation:** Checks PDF citations against retrieved document passages and removes unsupported references.
8. **Roadmap revision:** Allows learners to draft, review, apply, or discard proposed changes.
9. **Progress tracking:** Tracks completed and pending tasks and connects progress with the Roadmap Coach.
10. **Resource verification:** Checks learning resource URLs and distinguishes verified links from links that could not be verified.
11. **Progress export and import:** Allows learners to save and restore their progress.

## Automated Test Results

The latest local test run completed successfully.

| Test result | Count |
|---|---:|
| Tests collected | 110 |
| Tests passed | 110 |
| Subtests passed | 23 |
| Failed | 0 |
| Execution time | 4.11 seconds |

**Command used:**

```bash
python -m pytest -v
```

**Result:**

```text
110 passed, 23 subtests passed in 4.11s
```

These results represent the automated test run completed on the local development environment. They do not replace live API, deployment, or manual testing.

## Recording Tips

- Keep the browser and terminal text readable while recording.
- Avoid showing your Gemini API key, `.env` file, or other credentials.
- Use different content in the two PDFs so document replacement can be demonstrated clearly.
- Prepare your questions and sample inputs before recording.
- Keep the demonstration focused on actual application behaviour.
- Do not spend too much time waiting for API responses.
- If a feature fails during the recording, explain the result honestly rather than presenting an expected result as successful.

## Manual Testing Evidence

Before recording, complete the applicable manual test cases in `docs/TEST_EVIDENCE.md`.

Record the following for each case:

- Test case ID.
- Input or action performed.
- Expected result.
- Actual result observed.
- Pass or fail status.
- Screenshot or recording evidence, where required.

**Important:** The automated test results above are verified. Manual evaluation cases and screenshots must be completed separately using actual application observations.

## Project Documentation

Refer to these files for additional details:

- `README.md` – Project overview, features, installation, and usage.
- `docs/TEST_EVIDENCE.md` – Automated and manual testing evidence.
- `docs/DEMO_SCRIPT.md` – Demonstration steps and presentation timeline.
- `requirements.txt` – Main project dependencies.
- `requirements-dev.txt` – Development and testing dependencies.
- `requirements-lock.txt` – Locked environment dependencies.
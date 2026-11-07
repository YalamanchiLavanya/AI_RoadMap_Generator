# Test Evidence – AI Learning Roadmap Generator

## 1. Scope (Read This First)

| Layer | How It Was Tested | Status |
|---|---|---|
| Streaming, retry, validation, revision, progress, PDF indexing, link checking | Automated: 100 tests using `python -m pytest -v` | **100 passed, 23 subtests passed** |
| Gemini API | Replaced with a fake client that mimics SDK calls (`generate_content_stream`, `generate_content`), including scripted failures | Logic verified; real model output not tested |
| PDFs | Real PDFs generated using `reportlab` and read using `pypdf` | Automated PDF tests passed |
| Embeddings / FAISS | Deterministic fake embedder and NumPy search path | FAISS path and `all-MiniLM-L6-v2` model need live verification (L7) |
| Link checking | Local HTTP server returning 200/302/403/404/405/503 responses | Automated checks passed; real internet links need live verification (L10) |
| Streamlit UI | Not covered by unit tests; application logic is kept outside `app.py` | Needs live testing and demonstration |

### Automated Test Execution Details

- **Test command:** `python -m pytest -v`
- **Collection command:** `python -m pytest --collect-only -q`
- **Python version:** 3.12.10
- **Pytest version:** 9.2.0
- **Tests collected:** 100
- **Tests passed:** 100
- **Failed tests:** 0
- **Subtests passed:** 23
- **Execution time:** 4.78 seconds
- **Environment:** Windows, Python virtual environment (`.venv`)
- **Collection errors:** None
- **API key required:** No. Automated Gemini calls use a fake client.
- **Network required:** No. Automated tests use simulated/local services.

**Result: PASS**

The complete current test suite was successfully collected and executed. All 100 tests passed, with 23 additional subtests passing.

The previously incompatible `tests/test_roadmap.py` file is no longer part of the current repository. Current automated coverage is organized across the existing test modules. The removal of that file does not, by itself, establish that every historical test case was preserved.

**Important:** These results represent the local automated test run. They do not establish that the real Gemini API, embedding model, FAISS integration, or deployed Streamlit interface has been tested.

---

## 2. Documented Test Cases (Automated – Simulated Gemini)

| ID | Category | Scenario | Expected Result | Evidence (Test) | Result |
|---|---|---|---|---|---|
| A01 | Normal goal | SQL roadmap, Beginner, 8 hours/week × 4 weeks | Four numbered weeks, hours within limit, constraints stored | `GenerateRoadmap.test_valid_plan_on_first_try` | Pass |
| A02 | Unrealistic target | Become a Data Analyst, 64 total hours | Model is warned; plan states an achievable outcome and displays a reality-check banner | `TimeBudget.*`, `GenerateRoadmap.test_unrealistic_target_prompt_and_result`, `Presentation.test_unrealistic_plan_shows_a_reality_check...` | Pass |
| A03 | Unrealistic target | Model incorrectly considers the same goal realistic | Warning is added for the learner | `test_model_calling_an_unrealistic_goal_realistic_raises_a_warning` | Pass |
| A04 | Time budget | Week uses 12 hours against an 8-hour limit | Rejected and repaired once; repair prompt identifies the week | `test_invalid_plan_is_repaired_once`, `ValidatePlan.test_week_over_the_hour_limit` | Pass |
| A05 | Time budget | Week totals 8.5 hours against an 8-hour limit | Hours are scaled to fit, adjustment reported, no extra model call | `test_slightly_over_hours_are_fixed_without_another_model_call` | Pass |
| A06 | Invalid output | Plan remains invalid after repair due to missing milestone | `PlanValidationError`; invalid plan is not displayed | `test_plan_that_stays_invalid_is_rejected_not_shown` | Pass |
| A07 | Invalid output | JSON response is truncated | One repair request, followed by successful validation | `test_truncated_json_triggers_a_repair_request` | Pass |
| A08 | API failure | Invalid API key (401/403) | No retry; clear API-key error message | `RetryRules.test_invalid_api_key_is_not_retried` | Pass |
| A09 | API failure | Rate limit (429) occurs three times | Three attempts with 1-second and 2-second back-off; clear error message | `RetryRules.test_rate_limit_is_retried_then_reported_clearly` | Pass |
| A10 | API failure | 503 occurs before any text is generated | Automatic retry succeeds | `RetryRules.test_retry_happens_when_failure_comes_before_any_text` | Pass |
| A11 | Interrupted stream | Failure occurs after Week 1 text appears | No automatic restart; partial text returned in the error; Week 1 does not repeat | `RetryRules.test_failure_after_text_is_not_retried_and_nothing_repeats` | Pass |
| A12 | Interrupted stream | Roadmap stream breaks part-way | Partial output is discarded; clean restart; final roadmap contains Weeks 1–4 exactly once | `test_interrupted_stream_never_produces_a_duplicated_plan`, `test_collect_text_clears_partial_output_before_restarting` | Pass |
| A13 | PDF replacement | Index `syllabus.pdf`, then replace with `cooking.pdf` | Old document content becomes unreachable; results come only from the new document | `ReplaceAndRemove.test_replacing_a_document_removes_all_old_content` | Pass |
| A14 | PDF removal/change | Uploaded file is cleared or a different file is selected | Previous document index is cleared immediately | `test_removing_the_uploaded_file_clears_the_index`, `test_selecting_a_different_file_clears_the_old_index_immediately` | Pass |
| A15 | PDF page references | Ask a question about prerequisites | Retrieved result includes filename and page 3 | `Retrieval.test_hits_carry_filename_and_page`, `test_each_topic_maps_to_its_own_page` | Pass |
| A16 | PDF edge case | PDF contains no extractable text | Clear error message is displayed | `Extraction.test_pdf_without_text_gives_a_clear_error` | Pass |
| A17 | PDF in generation | Retrieved PDF pages are passed to roadmap generation | Prompt contains excerpts with page references; invented page numbers are removed | `test_source_pages_are_limited_to_retrieved_pages` | Pass |
| A18 | Roadmap revision | Draft a revision and then apply it | Draft does not change the current plan; applying updates display, download text, tracker, and export together | `RevisionFlow.test_drafting_does_not_change...`, `test_apply_updates_display_download_and_tracker_together` | Pass |
| A19 | Roadmap revision | Learner changes availability to 5 hours/week | New limit is validated and stored in the profile | `RevisionFlow.test_a_revision_may_lower_the_weekly_hours` | Pass |
| A20 | Roadmap revision | Revised plan exceeds its new weekly limit | Revision is rejected; current roadmap remains unchanged | `test_revision_that_breaks_the_new_limit_is_rejected_and_state_is_untouched` | Pass |
| A21 | Progress | Complete tasks and then revise the roadmap | Completed tasks remain completed; custom tasks are preserved | `test_completed_tasks_survive_a_revision` | Pass |
| A22 | Progress → Coach | Some roadmap tasks are completed | Coach prompt includes completed and pending tasks | `Tasks.test_coach_prompt_receives_completion_status` | Pass |
| A23 | Progress export | Export progress and restore it in a new session | Roadmap, completion flags, and custom tasks are restored; tampered/invalid files are rejected | `ExportImport.*` | Pass |
| A24 | Links | Test 200, redirect, 404, HEAD-rejected, 403, 503, and closed-port responses | Verified / verified / broken / verified / unverified / unverified / unverified | `CheckUrl.*` | Pass |
| A25 | Link safety | Test private, loopback, link-local, `file:` and `ftp:` URLs | Unsafe URLs are refused and never requested | `UrlSafety.*` | Pass |
| A26 | Link presentation | Display a mixture of link statuses | Only verified links are clickable and marked verified | `Presentation.test_only_verified_links_are_clickable...` | Pass |

---

## 3. Live Test Matrix (Real API Key Required)

The automated tests cannot determine whether Gemini produces useful, accurate, and personalized roadmaps.

The following tests must be performed manually using the real application and a valid Gemini API key.

| ID | Test Area | What to Test | Expected Result | Actual Result | Status |
|---|---|---|---|---|---|
| L01 | Gemini API | Generate a roadmap for a beginner learning Python | Gemini generates a valid, structured roadmap | Pending | Not tested |
| L02 | Personalization | Change experience level, current skills, and learning preferences | Roadmap adapts to the provided learner profile | Pending | Not tested |
| L03 | Time budget | Generate a roadmap with 5 hours/week | Weekly activities stay within the available time | Pending | Not tested |
| L04 | Duration | Generate a roadmap for 4 weeks and 8 weeks | Correct number of weeks and milestones are generated | Pending | Not tested |
| L05 | Streaming | Generate a roadmap and observe the response | Content appears progressively without unnecessary duplication | Pending | Not tested |
| L06 | Roadmap revision | Ask the coach to revise the existing roadmap and apply the changes | Updated roadmap appears consistently in the display, download, and tracker | Pending | Not tested |
| L07 | PDF RAG | Upload a real syllabus PDF and ask questions about its content | Relevant information is retrieved with correct document and page references using the actual embedding model and FAISS integration | Pending | Not tested |
| L08 | PDF replacement | Upload one PDF, replace it with another, and ask a question | Answers use only the newly uploaded document | Pending | Not tested |
| L09 | Progress tracking | Complete tasks, refresh the application, and export progress | Progress behaves as designed; exported data can be restored | Pending | Not tested |
| L10 | Resource links | Check actual internet resource URLs suggested in the roadmap | Links are correctly classified as verified, broken, or unverified | Pending | Not tested |
| L11 | Streamlit interface | Test all tabs, inputs, buttons, downloads, and navigation | UI works without crashes or unexpected behavior | Pending | Not tested |
| L12 | Error handling | Test an invalid API key, API outage, and network interruption | Clear error messages appear without exposing sensitive information | Pending | Not tested |
| L13 | Language support | Generate roadmaps in English, Telugu + English, and Hindi + English | Responses follow the selected language preference | Pending | Not tested |

### Live Testing Instructions

1. Activate the project virtual environment.
2. Configure a valid Gemini API key in the `.env` file or Streamlit secrets.
3. Start the application using:

   `streamlit run app.py`

4. Open the application in your browser.
5. Execute the live test cases from L01 to L13.
6. Record the actual result and update the status column.
7. Capture screenshots of important successful tests and any errors.
8. Verify the deployed Streamlit application separately from the local application.

**Evidence to Capture:**

- Screenshot of a successfully generated roadmap.
- Screenshot showing personalized weekly learning activities.
- Screenshot of streaming output.
- Screenshot of the Roadmap Coach revising an existing roadmap.
- Screenshot of PDF upload and document-based question answering.
- Screenshot showing PDF source references and page numbers.
- Screenshot of progress tracking and completed tasks.
- Screenshot of progress export and restoration.
- Screenshot of resource link verification.
- Screenshot of the complete Streamlit application.

---

## 4. Test Results Summary

### Automated Testing

| Metric | Result |
|---|---|
| Total automated tests collected | 100 |
| Passed tests | 100 |
| Failed tests | 0 |
| Subtests passed | 23 |
| Collection errors | 0 |
| Execution time | 4.78 seconds |
| Test framework | Pytest 9.2.0 |
| Python version | 3.12.10 |

**Automated Test Result: PASS**

All 100 automated tests passed successfully, with 23 additional subtests passing.

### Manual Testing

Manual testing is required to verify real Gemini responses, actual embedding generation, FAISS integration, internet resource links, and Streamlit UI behavior.

| Component | Status |
|---|---|
| Automated application logic | Passed |
| Simulated Gemini API behavior | Passed |
| Real Gemini API | Pending live verification |
| Actual embedding model | Pending live verification |
| FAISS integration | Pending live verification |
| Real internet link checking | Pending live verification |
| Streamlit UI | Pending live verification |
| Deployed application | Pending live verification |

---

## 5. Known Limitations and Testing Boundaries

1. **Gemini API:** Automated tests use a fake client. They verify application logic but do not prove real Gemini response quality or API availability.

2. **Embedding model:** Automated tests use a deterministic fake embedder. Actual `sentence-transformers/all-MiniLM-L6-v2` execution needs manual verification.

3. **FAISS:** The automated tests exercise the NumPy search path, not the actual FAISS integration.

4. **Internet links:** Automated link tests use a local HTTP server. Actual external websites may behave differently because of redirects, authentication, rate limits, or network restrictions. A successful HTTP response confirms reachability at the time of checking; it does not establish that a resource is relevant, current, beginner-friendly, or available in the selected language. Those qualities require separate content review.

5. **Streamlit UI:** Unit tests do not cover the complete browser interface. Manual testing is necessary.

6. **Progress persistence:** Progress tracking and export/import behavior are tested. Session persistence and restoration should be verified in the deployed environment.

---

## 6. Final Conclusion

The AI Learning Roadmap Generator successfully passed its local automated test suite, with **100 tests passed and 23 subtests passed**.

The automated tests cover roadmap generation logic, time-budget validation, error handling, streaming and retry behavior, PDF document processing, RAG retrieval logic, roadmap revision, progress tracking, export/import functionality, and resource link safety.

The remaining live tests are necessary to verify real Gemini API responses, actual embedding and FAISS integration, external resource links, and the deployed Streamlit interface.

**Overall conclusion:** The automated application logic has passed the documented test suite. Full end-to-end verification remains subject to completion of the live test matrix.
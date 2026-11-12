# Test Evidence – AI Learning Roadmap Generator

Repository: https://github.com/YalamanchiLavanya/AI_RoadMap_Generator

## 0. Test Run Information

| Item | Value |
|---|---|
| Tested commit | db7ef8210ac6df2b06165a544e7d9ea81c62361c |
| Date tested | [FILL: date of the automated run and of the live tests] |
| Operating system | Windows |
| Python version | 3.12.10 |
| Pytest version | 9.2.0 |
| Gemini model used in live tests | gemini-3.1-flash-lite |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Retrieval backend observed in the app | [FILL: FAISS or NumPy fallback, as shown in the app] |
| Dependency configuration | `requirements-lock.txt` (exact versions used for the recorded run) |

**How to read the status values in this document**

- **Passed** – the case was executed, an observation is recorded, and evidence is listed.
- **Pending** – the case has not been executed yet. No result is claimed.
- Automated results and manual (live) observations are reported separately.

---

## 1. Scope (Read This First)

| Layer | How It Was Tested | Status |
|---|---|---|
| Streaming, retry, validation, revision, progress, PDF indexing, link checking, coach context and citation handling | Automated: `python -m pytest -v` | See Section 4 for the recorded counts |
| Gemini API (automated) | Replaced with a fake client that mimics SDK calls (`generate_content_stream`, `generate_content`), including scripted failures | Logic verified; real model output is not tested by this layer |
| Gemini API (live) | Real API key, real application | L01–L04 Passed. L05, L06, L12 and L13 are Pending |
| PDFs | Real PDFs generated using `reportlab` and read using `pypdf` | Automated PDF tests only. Live PDF behaviour (L07, L08) is Pending |
| Embeddings / FAISS | Deterministic fake embedder and NumPy search path | Real embedding model and FAISS path are Pending (L07, L08) |
| Link checking | Local HTTP server returning 200/302/403/404/405/503 responses | Automated checks only. Real internet links (L10) are Pending |
| Streamlit UI | Not covered by unit tests; application logic is kept outside `app.py` where possible | Live UI testing (L11) is Pending |
| Deployed application | Not tested | Pending |

### Automated Test Execution Details

- **Test command:** `python -m pytest -v`
- **Collection command:** `python -m pytest --collect-only -q`
- **Environment:** Windows, Python virtual environment, installed from `requirements-dev.txt`
- **API key required:** No. Automated Gemini calls use a fake client.
- **Network required:** No. Automated tests use simulated/local services.

The recorded counts (tests collected, passed, failed, subtests, execution time) are in Section 4.

The previously incompatible `tests/test_roadmap.py` file is no longer part of the repository. Current automated coverage is organized across the existing test modules. The removal of that file does not, by itself, establish that every historical test case was preserved.

**Important:** The automated results do not establish that the real Gemini API, embedding model, FAISS integration, or deployed Streamlit interface has been tested. Those are covered only by the live cases in Section 3, and only the cases marked Passed there.

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
| A17 | PDF in generation | Retrieved PDF pages are passed to roadmap generation | Prompt contains excerpts with page references; page references outside the retrieved pages are removed | `test_source_pages_are_limited_to_retrieved_pages` | Pass |
| A18 | Roadmap revision | Draft a revision and then apply it | Draft does not change the current plan; applying updates display, download text, tracker, and export together | `RevisionFlow.test_drafting_does_not_change...`, `test_apply_updates_display_download_and_tracker_together` | Pass |
| A19 | Roadmap revision | Learner changes availability to 5 hours/week | New limit is validated and stored in the profile and the active plan constraints | `RevisionFlow.test_a_revision_may_lower_the_weekly_hours` | Pass |
| A20 | Roadmap revision | Revised plan exceeds its new weekly limit | Revision is rejected; current roadmap remains unchanged | `test_revision_that_breaks_the_new_limit_is_rejected_and_state_is_untouched` | Pass |
| A21 | Progress | Complete tasks and then revise the roadmap | Completed tasks remain completed; custom tasks are preserved | `test_completed_tasks_survive_a_revision` | Pass |
| A22 | Progress → Coach | Some roadmap tasks are completed | Coach prompt includes completed and pending tasks | `Tasks.test_coach_prompt_receives_completion_status` | Pass |
| A23 | Progress export | Export progress and restore it in a new session | Roadmap, completion flags, and custom tasks are restored; tampered/invalid files are rejected | `ExportImport.*` | Pass |
| A24 | Links | Test 200, redirect, 404, HEAD-rejected, 403, 503, and closed-port responses | Verified / verified / broken / verified / unverified / unverified / unverified | `CheckUrl.*` | Pass |
| A25 | Link safety | Test private, loopback, link-local, `file:` and `ftp:` URLs | Unsafe URLs are refused and never requested | `UrlSafety.*` | Pass |
| A26 | Link presentation | Display a mixture of link statuses | Only verified links are clickable and marked verified | `Presentation.test_only_verified_links_are_clickable...` | Pass |

### 2.1 Coach Context and Citation Tests (added after review)

These tests are in `tests/test_coach_context.py` and cover `coach_context.py` (`model_history`, `validate_coach_citations`). Confirm each result after running `python -m pytest tests/test_coach_context.py -v`, then change the Result column.

| ID | Category | Scenario | Expected Result | Evidence (Test) | Result |
|---|---|---|---|---|---|
| A27 | PDF context | Messages grounded in PDF A exist; PDF B becomes active | Messages derived from A are not sent to the model as current context; general conversation is kept | `CoachContextTests.test_replaced_pdf_context_is_not_sent_to_model` | Pass |
| A28 | PDF context | PDF is removed | No document-derived messages are sent to the model | `CoachContextTests.test_after_removal_no_document_messages_are_sent` | Pass |
| A29 | Coach citations | Answer cites one retrieved file/page and one that was not retrieved | The retrieved reference is kept; the other is replaced with an "unverified reference removed" marker | `CoachContextTests.test_invented_citation_is_removed_valid_one_kept` | Pass |
| A30 | Coach citations | No PDF is active but the answer contains a citation | Citation is removed | `CoachContextTests.test_citations_are_stripped_when_no_pdf_is_active` | Pass |
| A31 | PDF context | Index PDF A, replace with PDF B, then remove it | Retrieval uses B after replacement and nothing after removal; A-derived facts are absent from the messages sent to the model at each stage | `ReplacementFlow.test_pdf_a_then_b_then_removed` | Pass |
| A32 | Coach citations | Answer cites `(file.pdf, p. N)` for a retrieved file and page | Citation is kept | `CoachContextTests.test_valid_paren_citation_is_kept` | Pass |
| A33 | Coach citations | Answer cites a filename that was not retrieved | Citation is replaced with an "unverified reference removed" marker | `CoachContextTests.test_invalid_paren_filename_is_removed` | Pass |
| A34 | Coach citations | Answer cites the right file but a page that was not retrieved | Citation is replaced with the marker | `CoachContextTests.test_invalid_paren_page_is_removed` | Pass |
| A35 | Coach citations | No PDF is active but the answer contains a `(file.pdf, p. N)` citation | Citation is removed | `CoachContextTests.test_paren_citations_stripped_when_no_pdf_active` | Pass |
| A36 | PDF context | Remove a PDF when none was indexed | Nothing breaks; general messages are kept | `ReplacementFlow.test_removal_with_no_prior_pdf_is_harmless` | Pass |

**What these tests establish:** the application filters conversation history by the active document and removes citations that do not match retrieved passages. **What they do not establish:** that a retrieved page actually supports the claim it is attached to. That is assessed manually in Section 3.4.

---

## 3. Live Test Matrix (Real API Key Required)

The automated tests cannot determine whether Gemini produces useful, accurate, and personalized roadmaps. The cases below are executed manually using the real application and a valid Gemini API key.

### 3.1 Live Test Results

| ID | Test Area | What to Test | Expected Result | Actual Result | Evidence | Status |
|---|---|---|---|---|---|---|
| L01 | Gemini API | Generate a roadmap for a beginner learning Python | Gemini generates a valid, structured roadmap | Successfully generated a four-week Python roadmap using the real Gemini API. The roadmap contained structured weekly learning activities. | `docs/evidence/L01_gemini_roadmap.png` | Passed |
| L02 | Personalization | Change experience level, current skills, and learning preferences | Roadmap adapts to the provided learner profile | Beginner and intermediate roadmaps were generated. The learning activities changed according to the selected experience level, skills, and preferences. | `docs/evidence/L02_intermediate_roadmap.png` (intermediate roadmap only) | Passed |
| L03 | Weekly time budget | Generate a roadmap with 5 available hours per week | Each week's planned study time stays within 5 hours | All four weeks stayed within the 5-hour weekly limit. | `docs/evidence/L03_gemini_roadmap.png` | Passed |
| L04 | Roadmap duration | Generate roadmaps for 4-week and 8-week durations | Generated roadmaps contain the selected number of weeks | Both 4-week and 8-week roadmaps contained the correct number of weeks. | `docs/evidence/L04_gemini_roadmap.png` | Passed |
| L05 | Streaming | Generate an 8-week roadmap and test an interrupted generation | Content streams progressively without duplicated weeks after retry | Not yet executed. | None yet | Pending |
| L06 | Roadmap revision | Revise an existing roadmap and apply the changes | Revised roadmap updates the saved roadmap, downloads, progress tracker, and the active-roadmap settings line | Not yet executed. | None yet | Pending |
| L07 | PDF upload and RAG | Upload a PDF and ask questions about its content | Answers are based on the uploaded PDF and include relevant source references | Not yet executed. | None yet | Pending |
| L08 | PDF replacement and removal | Replace an uploaded PDF and then remove it | Old document content is no longer retrieved or supplied as current evidence after replacement or removal | Not yet executed. | None yet | Pending |
| L09 | Progress tracking | Complete tasks, refresh the app, export progress, and import it again | Progress is preserved or restored correctly after refresh and import | Not yet executed. | None yet | Pending |
| L10 | Resource link verification | Open generated learning resource links and review their content | Link reachability is recorded accurately, and resource relevance is manually assessed | Not yet executed. | None yet | Pending |
| L11 | Streamlit UI | Test all tabs, input controls, navigation, and download buttons | All UI components work correctly without unexpected errors | Not yet executed. | None yet | Pending |
| L12 | Error handling | Test missing API configuration, invalid API key, API outage, and interrupted generation | Clear error messages are displayed without exposing secrets or crashing unexpectedly | Not yet executed. | None yet | Pending |
| L13 | Language support | Generate roadmaps in English, Telugu + English, and Hindi + English | Generated roadmaps follow the selected language preference | Not yet executed. | None yet | Pending |

**Evidence notes for the Passed cases**

- L01–L04 are supported by static screenshots of generated roadmaps. They show the generated output; they do not show the underlying Gemini request.
- L02 shows the intermediate roadmap only. The beginner roadmap used for comparison is not in a separate screenshot.

**Rules for updating this table**

1. Change a case to Passed only after executing it, and replace "Not yet executed." with: the input used, what was observed, and the test environment.
2. Every Passed case must list an evidence file that exists in `docs/evidence/` and that shows the claimed behaviour.
3. Multi-step workflows (interrupted generation, revision, PDF replacement/removal, progress restoration) need a short recording, not a single screenshot.
4. After changing any row, update Section 4 so the summary agrees with the rows.

### Live Testing Instructions

1. Activate the project virtual environment.
2. Configure a valid Gemini API key in the `.env` file or Streamlit secrets. Do not include the key in screenshots, recordings, or committed files.
3. Start the application using `streamlit run app.py`.
4. Open the application in your browser.
5. Execute each Pending case (L05–L13) and record the observation in the table above.
6. Capture the evidence listed below for each case.
7. Verify the deployed Streamlit application separately from the local application.

**Evidence needed for each pending case**

| Case | Evidence |
|---|---|
| L05 | Short recording: progressive output, interruption, retry, no duplicated week |
| L06 | Recording: draft, apply, then Roadmap tab, download, tracker and active-settings line |
| L07 | Screenshot: question, answer with source reference, and the cited PDF page |
| L08 | Recording: ask about PDF A, replace with B, ask again, remove the PDF |
| L09 | Recording: complete tasks, export, refresh, import, tasks restored |
| L10 | Screenshot of link results, plus the review table in Section 3.3 |
| L11 | Screenshot or recording of all tabs, controls and downloads; note any problem |
| L12 | One screenshot per error case; state any sub-case that was not tested |
| L13 | One screenshot per language |

### 3.2 Active Roadmap Settings (manual check, part of L06)

After applying a revision, the Roadmap tab and the Progress tab show the active plan's weekly hours, duration and version. The sidebar sliders are labelled as inputs for generating a new roadmap. Downloaded Markdown states the active settings. Record the observed behaviour with L06.

### 3.3 Resource Review (L10)

HTTP reachability and learning-resource quality are recorded separately. This table is completed when L10 is executed.

| Resource | HTTP status (checker) | Relevant to the topic? | Current? | Appropriate for the learner's level? | Suitable for the selected language? |
|---|---|---|---|---|---|
| Pending – L10 not yet executed | | | | | |

### 3.4 Coach Citation Evaluation (manual)

Each answer is checked against the cited passage. A valid page number is not treated as proof of factual support.

| Question type | Question asked | Answer summary | Cited file and page | Text on that page | Supports the claim? (Yes / Partial / No) |
|---|---|---|---|---|---|
| Supported | Pending | | | | |
| Partially supported | Pending | | | | |
| Not covered by the PDF | Pending | | | | |

For the "not covered" question, the expected behaviour is that the coach states the PDF does not cover it, with no invented file or page reference.

---

## 4. Test Results Summary

### Automated Testing

| Metric | Result |
|---|---|
| Total automated tests collected | 110 |
| Passed tests | 110 |
| Failed tests | 0 |
| Subtests passed | 23 |
| Collection errors | 0 |
| Execution time | 4.11 seconds |
| Test framework | Pytest 9.2.0 |
| Python version | 3.12.10 |

Record these from a clean installation using `requirements-dev.txt` (or `requirements-lock.txt`) and `python -m pytest -v`. Use the same test count in `README.md` and `docs/DEMO_SCRIPT.md`.

### Manual Testing

| Component | Evidence | Status |
|---|---|---|
| Automated application logic | Section 2 | Passed once the counts above are recorded |
| Simulated Gemini API behaviour | A01–A12 | Passed once the counts above are recorded |
| Real Gemini API – roadmap generation, personalization, time budget, duration | L01–L04 | Passed |
| Real Gemini API – streaming, revision, error handling, language | L05, L06, L12, L13 | Pending |
| Actual embedding model | L07 | Pending |
| FAISS integration | L07, L08 | Pending |
| Real internet link checking | L10 | Pending |
| Streamlit UI | L11 | Pending |
| Progress export/import in the live app | L09 | Pending |
| Deployed application | Not tested | Pending |

---

### Resource Verification Limitations

The link checker verifies HTTP reachability only.

- Reachable: The URL returned a successful HTTP response.
- Broken: The URL returned a clear client error.
- Unverified: The URL could not be checked reliably.
- Invalid: The URL is not a valid supported HTTP/HTTPS URL.
- No link: The resource did not contain a URL.

HTTP reachability does not establish content relevance, freshness, beginner-friendliness, or language suitability. These resource-quality characteristics are assessed manually in the review table in Section 3.3 (L10). `assess_resource_quality()` records assessments; the helper's existence does not mean the reviews have been completed.

---

## 5. Known Limitations and Testing Boundaries

1. **Gemini API:** Automated tests use a fake client. They verify application logic but do not prove real Gemini response quality or API availability. Live evidence is limited to the cases marked Passed in Section 3.1.

2. **Embedding model:** Automated tests use a deterministic fake embedder. Actual `sentence-transformers/all-MiniLM-L6-v2` execution is verified only when L07 is Passed.

3. **FAISS:** The automated tests exercise the NumPy search path, not the actual FAISS integration. FAISS is verified only when L07/L08 are Passed with the FAISS backend visible.

4. **Internet links:** Automated link tests use a local HTTP server. Actual external websites may behave differently because of redirects, authentication, rate limits, or network restrictions. A successful HTTP response confirms reachability at the time of checking; it does not establish that a resource is relevant, current, beginner-friendly, or available in the selected language.

5. **Citation checking scope:** Roadmap generation restricts page references to the retrieved pages. Coach answers are checked so that filename/page references not present in the retrieved passages are removed. Both checks establish that a referenced page was retrieved. Neither establishes that the page supports the associated claim; that requires the manual evaluation in Section 3.4.

6. **PDF context:** After a PDF is replaced or removed, messages derived from the earlier document are excluded from the context sent to the model, and are labelled as earlier-document content in the interface. General roadmap conversation is kept. This is verified by the automated tests in Section 2.1; the live behaviour is verified by L08.

7. **Streamlit UI:** Unit tests do not cover the complete browser interface. Live testing (L11) is required.

8. **Progress persistence:** Progress export/import is covered by automated tests. Restoration in the live and deployed applications is verified only when L09 is Passed.

---

## 6. Final Conclusion

The automated test suite covers roadmap generation logic, time-budget validation, error handling, streaming and retry behaviour, PDF document processing, RAG retrieval logic, coach context handling after PDF replacement or removal, coach citation filtering, roadmap revision, progress tracking, export/import functionality, and resource link safety. The recorded counts are in Section 4.

Live evidence currently covers roadmap generation with the real Gemini API (L01–L04). The following remain Pending and are not claimed as verified: interrupted-generation retry, live revision, PDF retrieval with the real embedding model and FAISS, PDF replacement/removal, progress restoration, resource review, UI testing, error handling, language support, and the deployed application.

**Overall conclusion:** Automated application logic is covered by the documented suite. End-to-end verification is partial: live cases L01–L04 are Passed, and L05–L13 and the deployed application are Pending until executed and evidenced as described in Section 3.
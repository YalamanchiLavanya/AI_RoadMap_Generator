# Test Evidence - AI Learning Roadmap Generator

## 1. Scope (read this first)

| Layer | How it was tested | Status |
|---|---|---|
| Streaming, retry, validation, revision, progress, PDF indexing, link checking | **Automated**: 100 tests, `python -m unittest discover -s tests -t .` | **100 / 100 passed** |
| Gemini API | Replaced by a fake client that mimics the SDK calls (`generate_content_stream`, `generate_content`), including scripted failures | Logic verified; **real model output not tested** |
| PDFs | Real PDFs generated with `reportlab`, read with `pypdf` | Verified |
| Embeddings / FAISS | Deterministic fake embedder; NumPy search path. The FAISS path and the `all-MiniLM-L6-v2` model are **not** exercised in the automated run | Needs live check (L7) |
| Link checking | Local HTTP server returning 200/302/403/404/405/503 | Verified; real internet links need live check (L10) |
| Streamlit UI | Not covered by the unit tests; the app logic is kept out of `app.py` on purpose | Needs live check / demo |

The 100 tests run in under a second with no API key and no network.

## 2. Documented cases (automated, simulated Gemini)

| ID | Category | Scenario | Expected | Evidence (test) | Result |
|---|---|---|---|---|---|
| A01 | Normal goal | SQL roadmap, Beginner, 8 h/week x 4 weeks | 4 numbered weeks, hours within limit, constraints stored | `GenerateRoadmap.test_valid_plan_on_first_try` | Pass |
| A02 | Unrealistic target | "Become a Data Analyst", 64 h total | Model is warned; plan says *not realistic* and states an achievable outcome; reality-check banner rendered | `TimeBudget.*`, `GenerateRoadmap.test_unrealistic_target_prompt_and_result`, `Presentation.test_unrealistic_plan_shows_a_reality_check...` | Pass |
| A03 | Unrealistic target (model disagrees) | Model calls the same goal realistic | Warning added for the learner | `test_model_calling_an_unrealistic_goal_realistic_raises_a_warning` | Pass |
| A04 | Time budget | Week uses 12 h of an 8 h limit | Rejected, repaired once, repair prompt names the week | `test_invalid_plan_is_repaired_once`, `ValidatePlan.test_week_over_the_hour_limit` | Pass |
| A05 | Time budget (small overrun) | Week totals 8.5 h of 8 h | Scaled to fit, change reported, no extra model call | `test_slightly_over_hours_are_fixed_without_another_model_call` | Pass |
| A06 | Invalid output | Plan still invalid after repair (missing milestone) | `PlanValidationError`; nothing shown | `test_plan_that_stays_invalid_is_rejected_not_shown` | Pass |
| A07 | Invalid output | JSON cut off mid-reply | One repair request, then success | `test_truncated_json_triggers_a_repair_request` | Pass |
| A08 | API failure | Invalid API key (401/403) | No retry; message mentions the API key | `RetryRules.test_invalid_api_key_is_not_retried` | Pass |
| A09 | API failure | Rate limit (429) three times | 3 attempts with back-off 1 s, 2 s; clear message | `RetryRules.test_rate_limit_is_retried_then_reported_clearly` | Pass |
| A10 | API failure | 503 before any text | Automatic retry succeeds | `RetryRules.test_retry_happens_when_failure_comes_before_any_text` | Pass |
| A11 | Interrupted stream | Failure after "Week 1" text appeared (the reviewer's repeated-Week-1 scenario) | No automatic restart; partial text returned in the error; "Week 1" appears once | `RetryRules.test_failure_after_text_is_not_retried_and_nothing_repeats` | Pass |
| A12 | Interrupted stream | Plan stream breaks part-way | Partial discarded, clean restart, final plan has weeks 1-4 once | `test_interrupted_stream_never_produces_a_duplicated_plan`, `test_collect_text_clears_partial_output_before_restarting` | Pass |
| A13 | PDF replacement | Index syllabus.pdf, then cooking.pdf | Old content unreachable; hits come only from the new file | `ReplaceAndRemove.test_replacing_a_document_removes_all_old_content` | Pass |
| A14 | PDF removal / change | Uploader cleared, or different file selected | Index cleared immediately | `test_removing_the_uploaded_file_clears_the_index`, `test_selecting_a_different_file_clears_the_old_index_immediately` | Pass |
| A15 | PDF page references | Question about prerequisites | Hit carries file name and page 3 | `Retrieval.test_hits_carry_filename_and_page`, `test_each_topic_maps_to_its_own_page` | Pass |
| A16 | PDF edge case | PDF with no extractable text | Clear error message | `Extraction.test_pdf_without_text_gives_a_clear_error` | Pass |
| A17 | PDF in generation | Retrieved pages passed to generation | Prompt contains excerpts with pages; model-invented page numbers are dropped | `test_source_pages_are_limited_to_retrieved_pages` | Pass |
| A18 | Roadmap revision | Draft a revision, then apply | Draft leaves the plan untouched; apply updates display, download text, tracker and export together | `RevisionFlow.test_drafting_does_not_change...`, `test_apply_updates_display_download_and_tracker_together` | Pass |
| A19 | Roadmap revision | Learner now has only 5 h/week | New limit validated and stored in the profile | `RevisionFlow.test_a_revision_may_lower_the_weekly_hours` | Pass |
| A20 | Roadmap revision | Revised plan breaks its own new limit | Rejected; current roadmap unchanged | `test_revision_that_breaks_the_new_limit_is_rejected_and_state_is_untouched` | Pass |
| A21 | Progress | Completed tasks, then a revision | Completed tasks stay done; custom tasks kept | `test_completed_tasks_survive_a_revision` | Pass |
| A22 | Progress -> coach | Some tasks done | Coach prompt lists completed and open tasks | `Tasks.test_coach_prompt_receives_completion_status` | Pass |
| A23 | Progress export | Export, then restore in a new session | Plan, done flags and custom tasks restored; tampered/invalid files rejected | `ExportImport.*` | Pass |
| A24 | Links | 200, redirect, 404, HEAD-rejected, 403, 503, closed port | Verified / verified / broken / verified / unverified / unverified / unverified | `CheckUrl.*` | Pass |
| A25 | Links - safety | Private, loopback, link-local, `file:`/`ftp:` URLs | Refused, never requested | `UrlSafety.*` | Pass |
| A26 | Links - presentation | Mixed link statuses | Only verified links clickable and marked verified | `Presentation.test_only_verified_links_are_clickable...` | Pass |

## 3. Live test matrix (to be run with a real API key)

The automated cases cannot judge whether Gemini writes a *good* roadmap. Run these in the real app,
fill in the last two columns, and keep screenshots or a recording. Nothing below has been run yet.

| ID | Goal | Level | Hours/week x weeks | What to check | Actual result | Pass/Fail |
|---|---|---|---|---|---|---|
| L1 | Data Analyst | Beginner | 8 x 8 | Reality-check banner shown; achievable outcome sensible | | |
| L2 | Python Developer | Beginner (no programming) | 10 x 12 | Starts at fundamentals; every week <= 10 h | | |
| L3 | Frontend Developer (knows HTML/CSS) | Intermediate | 12 x 10 | JavaScript, React, APIs; no repeated HTML/CSS basics | | |
| L4 | Machine Learning | Beginner (basic Python) | 10 x 16 | Maths/data handling before models | | |
| L5 | Power BI Analyst | Beginner | 4 x 4 | Short practical plan; hours within limit | | |
| L6 | Any goal | Beginner | 2 x 6 | Minimum hours respected; scope clearly cut down | | |
| L7 | Upload a real syllabus PDF, index it, generate | Any | 8 x 8 | Page references appear; coach answers cite pages (this also exercises the real embedding model and FAISS) | | |
| L8 | Replace the PDF with another file | - | - | Old index cleared; answers come only from the new file | | |
| L9 | Ask the coach to cut Week 2 to 5 h, draft and apply | - | - | Roadmap tab, download and tracker all change; completed tasks kept | | |
| L10 | Click through 3-5 recommended links | - | - | Links marked verified really open; broken ones are labelled | | |
| L11 | Cybersecurity Analyst / Java Backend Developer | Beginner / Intermediate | 10 x 12 | Relevant topics, hands-on practice, milestones | | |
| L12 | Remove the API key, then start | - | - | Clear configuration message, no crash | | |
| L13 | Turn Wi-Fi off during generation | - | - | Friendly error; no half-written plan saved | | |

## 4. Demo / recording

See `docs/DEMO_SCRIPT.md` for a 6-7 minute walkthrough that covers every feedback point. A live
demo or recording still has to be made by the learner on their own machine.

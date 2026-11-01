"""AI Learning Roadmap Generator - Streamlit interface.

This file only handles the interface. Logic lives in:
  config.py         settings, limits, client creation
  prompts.py        roadmap, revision, and coach prompts
  roadmap_engine.py generation, streaming retries, validation, revision
  rag_system.py     PDF extraction, indexing, retrieval
  progress.py       tasks, completion, export/import, state changes
  link_checker.py   verifies recommended links
"""
from datetime import date

import streamlit as st


def apply_custom_css():
    st.markdown("""
    <style>

    /* =================================
       GLOBAL BACKGROUND
    ================================= */

    .stApp {
        background: #0B1120 !important;
        color: #F8FAFC !important;
    }

    [data-testid="stAppViewContainer"] {
        background: #0B1120 !important;
    }

    [data-testid="stMain"] {
        background: #0B1120 !important;
    }

    [data-testid="stHeader"] {
        background: #0B1120 !important;
    }

    [data-testid="stMainBlockContainer"] {
        background: transparent !important;
    }

    /* =================================
       SIDEBAR
    ================================= */

    [data-testid="stSidebar"] {
        background: #111827 !important;
        border-right: 1px solid #293449;
    }

    [data-testid="stSidebar"] > div {
        background: #111827 !important;
    }

    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #E2E8F0 !important;
    }

    /* =================================
       ALL TEXT
    ================================= */

    h1, h2, h3, h4, h5, h6 {
        color: #F8FAFC !important;
    }

    p, li, label, span, strong, em {
        color: #E2E8F0;
    }

    [data-testid="stMarkdownContainer"] {
        color: #E2E8F0 !important;
    }

    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] li {
        color: #E2E8F0 !important;
    }

    /* =================================
       INPUT FIELDS
    ================================= */

    .stTextInput input,
    .stTextArea textarea,
    .stNumberInput input {
        background: #1E293B !important;
        color: #FFFFFF !important;
        border: 1px solid #475569 !important;
        border-radius: 10px !important;
    }

    .stTextInput input::placeholder,
    .stTextArea textarea::placeholder {
        color: #94A3B8 !important;
    }

    /* =================================
       DROPDOWN
    ================================= */

    [data-baseweb="select"] > div {
        background: #1E293B !important;
        color: #FFFFFF !important;
        border-color: #475569 !important;
    }

    [data-baseweb="select"] span {
        color: #FFFFFF !important;
    }

    [data-baseweb="popover"],
    [data-baseweb="menu"] {
        background: #1E293B !important;
    }

    [role="option"] {
        background: #1E293B !important;
        color: #FFFFFF !important;
    }

    [role="option"]:hover {
        background: #334155 !important;
    }

    /* =================================
       BUTTONS
    ================================= */

    .stButton > button,
    .stDownloadButton > button {
        background: linear-gradient(
            90deg,
            #7C3AED,
            #4F46E5
        ) !important;

        color: #FFFFFF !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 10px 20px !important;
        font-weight: 600 !important;
        transition: 0.3s ease;
    }

    .stButton > button:hover,
    .stDownloadButton > button:hover {
        background: linear-gradient(
            90deg,
            #6D28D9,
            #4338CA
        ) !important;
        border: 1px solid #A78BFA !important;
        transform: translateY(-2px);
    }

    /* =================================
       TABS
    ================================= */

    .stTabs [data-baseweb="tab-list"] {
        background: #111827 !important;
        gap: 10px;
    }

    .stTabs [data-baseweb="tab"] {
        background: transparent !important;
        color: #CBD5E1 !important;
    }

    .stTabs [data-baseweb="tab"] p {
        color: #CBD5E1 !important;
    }

    .stTabs [aria-selected="true"] {
        color: #A78BFA !important;
        border-bottom: 3px solid #8B5CF6 !important;
    }

    /* =================================
       CARDS AND METRICS
    ================================= */

    [data-testid="stMetric"] {
        background: #151E30 !important;
        border: 1px solid #334155 !important;
        border-radius: 12px !important;
        padding: 18px !important;
    }

    [data-testid="stMetricLabel"],
    [data-testid="stMetricValue"] {
        color: #F8FAFC !important;
    }

    [data-testid="stExpander"] {
        background: #151E30 !important;
        border: 1px solid #334155 !important;
        border-radius: 10px !important;
    }

    /* =================================
       ALERTS AND NOTIFICATIONS
    ================================= */

    [data-testid="stAlert"] {
        background: #1E293B !important;
        color: #F8FAFC !important;
        border: 1px solid #475569 !important;
        border-radius: 10px !important;
    }

    [data-testid="stAlert"] p {
        color: #F8FAFC !important;
    }

    /* =================================
       SLIDER
    ================================= */

    [data-testid="stSlider"] {
        color: #A78BFA !important;
    }

    [data-testid="stSlider"] label {
        color: #E2E8F0 !important;
    }

    /* =================================
       FILE UPLOADER
    ================================= */

    [data-testid="stFileUploader"] {
        background: #151E30 !important;
        border: 1px dashed #64748B !important;
        border-radius: 12px !important;
        padding: 10px !important;
    }

    [data-testid="stFileUploader"] section {
        background: #151E30 !important;
    }

    [data-testid="stFileUploader"] button {
        color: #FFFFFF !important;
        background: #334155 !important;
    }

    /* =================================
       CHECKBOX AND RADIO
    ================================= */

    [data-testid="stCheckbox"] label,
    [data-testid="stRadio"] label {
        color: #E2E8F0 !important;
    }

    /* =================================
       LINKS
    ================================= */

    a {
        color: #A78BFA !important;
    }

    a:hover {
        color: #C4B5FD !important;
    }

    /* =================================
       DATAFRAME AND TABLE
    ================================= */

    [data-testid="stDataFrame"],
    [data-testid="stTable"] {
        background: #151E30 !important;
        color: #F8FAFC !important;
    }

    /* =================================
       DIVIDERS
    ================================= */

    hr {
        border-color: #334155 !important;
    }

    /* =================================
       SCROLLBAR
    ================================= */

    ::-webkit-scrollbar {
        width: 8px;
    }

    ::-webkit-scrollbar-track {
        background: #0B1120;
    }

    ::-webkit-scrollbar-thumb {
        background: #475569;
        border-radius: 10px;
    }

    </style>
    """, unsafe_allow_html=True)


apply_custom_css()


import progress
import prompts
import rag_system
from config import (
    LEARNING_STYLES,
    LEVELS,
    MAX_HOURS_PER_WEEK,
    MAX_WEEKS,
    MIN_HOURS_PER_WEEK,
    MIN_WEEKS,
    RESOURCE_LANGUAGES,
    LearnerProfile,
    create_client,
)
from link_checker import check_links
from roadmap_engine import (
    GenerationError,
    PlanValidationError,
    StreamInterruptedError,
    collect_urls,
    generate_response,
    generate_roadmap,
    plan_check_summary,
    plan_outline,
    plan_to_markdown,
    revise_roadmap,
    stream_progress,
)

st.set_page_config(page_title="AI Learning Roadmap Generator", page_icon="🧭", layout="wide")
ss = st.session_state
progress.init_state(ss)

st.markdown(
    """
<style>
.stApp { background: linear-gradient(135deg, #f5f7ff, #eef4ff, #f8f5ff); }
.block-container { max-width: 1200px; padding-top: 1.5rem; }
.hero { background: linear-gradient(110deg, #172554, #4338ca); padding: 28px;
        border-radius: 18px; color: white; margin-bottom: 20px; }
.hero h1 { color: white; }
</style>
<div class="hero">
  <h1>🧭 AI Learning Roadmap Generator</h1>
  <p>Turn your career goal into a checked, personalised weekly plan with milestones,
     verified resources, and progress tracking.</p>
</div>
""",
    unsafe_allow_html=True,
)


# ==========================================================================
# Helpers (interface only)
# ==========================================================================
@st.cache_resource(show_spinner=False)
def get_llm():
    return create_client()


def refresh_links(force: bool = False) -> None:
    """Check recommended links (only the ones not checked yet unless forced)."""
    plan = ss.roadmap_plan
    if not plan:
        return
    urls = collect_urls(plan)
    todo = urls if force else [u for u in urls if u not in ss.link_results]
    if todo:
        with st.spinner("Checking the recommended links..."):
            ss.link_results = {**ss.link_results, **check_links(todo)}
        ss.links_checked_on = date.today().strftime("%d %b %Y")


def show_client_problem() -> None:
    st.error("Gemini is not configured, so nothing can be generated yet.")
    st.code(client_error or "Unknown configuration error.")


try:
    client, settings = get_llm()
    client_error = None
except Exception as exc:  # noqa: BLE001 - shown to the learner instead of crashing
    client, settings, client_error = None, None, str(exc)


# ==========================================================================
# Sidebar: learner profile and optional PDF
# ==========================================================================
with st.sidebar:
    st.header("🎯 Your Learning Profile")
    goal = st.text_input("Career goal", value="Become a Data Analyst")
    current_skills = st.text_area("Current skills", value="Python basics, Excel basics")
    level = st.selectbox("Current skill level", LEVELS)
    hours_per_week = st.slider("Study hours per week", MIN_HOURS_PER_WEEK, MAX_HOURS_PER_WEEK, 10)
    duration_weeks = st.slider("Roadmap duration (weeks)", MIN_WEEKS, MAX_WEEKS, 8)
    learning_style = st.selectbox("Preferred learning style", LEARNING_STYLES)
    learning_language = st.selectbox("Resource language", RESOURCE_LANGUAGES)
    generate_clicked = st.button("✨ Generate My Roadmap", type="primary", use_container_width=True)

    st.divider()
    st.subheader("📄 Optional PDF (syllabus or guide)")
    uploaded_pdf = st.file_uploader("Upload a PDF", type=["pdf"], key="pdf_uploader")
    uploaded_bytes = uploaded_pdf.getvalue() if uploaded_pdf else None
    uploaded_hash = rag_system.file_digest(uploaded_bytes) if uploaded_bytes else None

    # The index must always belong to the file that is currently selected.
    sync = rag_system.sync_pdf_state(ss, uploaded_hash)
    if sync == "removed":
        st.info("The PDF was removed, so its index was cleared.")
    elif sync == "replaced":
        st.info("A different PDF was selected. The old index was cleared - index the new file to use it.")

    pdf_index = rag_system.get_pdf_index(ss)
    if pdf_index:
        st.success(
            f"Indexed: **{pdf_index.filename}** - {pdf_index.page_count} pages, "
            f"{len(pdf_index.chunks)} passages ({pdf_index.backend})."
        )
    elif uploaded_pdf:
        st.warning("This PDF is selected but not indexed yet.")

    if st.button("Index this PDF", use_container_width=True, disabled=uploaded_pdf is None):
        try:
            with st.spinner("Reading the PDF and building the search index..."):
                new_index = rag_system.build_pdf_index(uploaded_bytes, uploaded_pdf.name)
            replaced = rag_system.set_pdf_index(ss, new_index)
            st.success("PDF indexed." + (f" It replaced {replaced}." if replaced else ""))
            st.rerun()
        except rag_system.PdfError as exc:
            st.error(str(exc))
        except Exception as exc:  # noqa: BLE001
            st.error(f"PDF processing failed: {exc}")
    use_pdf_for_generation = st.checkbox(
        "Use the indexed PDF when generating the roadmap",
        value=True,
        disabled=pdf_index is None,
        help="The coach and roadmap revisions use the indexed PDF either way.",
    )
    if pdf_index and st.button("Clear PDF index", use_container_width=True):
        rag_system.clear_pdf_index(ss)
        st.rerun()

if client is None:
    st.warning("Gemini is not configured. Add GEMINI_API_KEY (see README) and reload.")
    with st.expander("Configuration details"):
        st.code(client_error or "Unknown configuration error.")

tab_roadmap, tab_coach, tab_progress, tab_design = st.tabs(
    ["🗺️ Roadmap", "💬 Roadmap Coach", "✅ Progress Tracker", "🧠 How it works"]
)

# ==========================================================================
# Tab 1 - Roadmap
# ==========================================================================
with tab_roadmap:
    st.subheader("Your Personalised Learning Plan")

    if generate_clicked:
        profile = LearnerProfile(
            goal=goal.strip(),
            current_skills=current_skills.strip() or "Not specified",
            level=level,
            hours_per_week=hours_per_week,
            duration_weeks=duration_weeks,
            learning_style=learning_style,
            learning_language=learning_language,
        )
        problems = profile.problems()
        if problems:
            for problem in problems:
                st.error(problem)
        elif client is None:
            show_client_problem()
        else:
            hits = []
            if pdf_index and use_pdf_for_generation:
                hits = rag_system.retrieve_for_generation(ss, profile)
                if hits:
                    st.caption(f"Using your PDF: {rag_system.summarize_sources(hits)}")
                else:
                    st.caption("Your PDF had nothing relevant to this goal, so it was not used.")
            bar = st.progress(0.0, text="Drafting your roadmap...")
            status = st.empty()

            def on_chunk(text):
                done = stream_progress(text, profile.duration_weeks)
                bar.progress(done, text=f"Drafting your roadmap... {round(done * 100)}%")

            def on_reset():
                bar.progress(0.0, text="The connection dropped - starting this step again from a clean slate...")

            try:
                result = generate_roadmap(
                    client, profile, settings=settings, hits=hits,
                    on_chunk=on_chunk, on_reset=on_reset, on_status=status.info,
                )
            except PlanValidationError as exc:
                st.error("The generated plan broke your limits even after one repair attempt, so it was not shown.")
                with st.expander("What was wrong"):
                    for line in exc.errors:
                        st.write(f"- {line}")
                st.info("Try again, or adjust the hours and duration slightly.")
            except GenerationError as exc:
                st.error(str(exc))
            except Exception as exc:  # noqa: BLE001
                st.error(f"Roadmap generation failed: {exc}")
            else:
                progress.load_plan(
                    ss, result.plan, profile.to_dict(),
                    warnings=result.warnings, notes=result.notes,
                )
                refresh_links()
                st.success("Your roadmap is ready.")
            finally:
                bar.empty()
                status.empty()

    plan = ss.roadmap_plan
    if plan:
        st.caption(plan_check_summary(plan) + f" · version {ss.plan_version}")
        if ss.plan_warnings or ss.plan_notes:
            with st.expander("Notes from the plan check", expanded=False):
                for line in ss.plan_notes + ss.plan_warnings:
                    st.write(f"- {line}")
        markdown = progress.plan_markdown_for_state(ss, ss.links_checked_on)
        st.markdown(markdown)
        left, right = st.columns(2)
        left.download_button(
            "⬇️ Download roadmap (Markdown)", data=markdown,
            file_name="learning_roadmap.md", mime="text/markdown",
        )
        if right.button("🔗 Re-check links"):
            refresh_links(force=True)
            st.rerun()
    else:
        st.info("Fill in your profile in the sidebar and click **Generate My Roadmap**. "
                "You can also restore saved progress in the Progress Tracker tab.")

# ==========================================================================
# Tab 2 - Roadmap Coach
# ==========================================================================
with tab_coach:
    st.subheader("Chat with Your Roadmap Coach")
    st.write("Ask questions about your plan. To change the plan itself, use **Revise the roadmap** below.")

    if not ss.roadmap_plan:
        st.info("Generate a roadmap first to start a conversation.")
    else:
        pending = ss.pending_revision
        if pending:
            with st.container(border=True):
                st.markdown("### 📝 Drafted revision - not applied yet")
                st.caption(f"Request: {pending['instruction']}")
                st.markdown("**What changes**")
                for line in pending["change_summary"]:
                    st.write(f"- {line}")
                if pending["changed_weeks"]:
                    st.caption("Weeks that differ: " + ", ".join(str(w) for w in pending["changed_weeks"]))
                for line in pending["notes"] + pending["warnings"]:
                    st.caption(f"ℹ️ {line}")
                with st.expander("Preview the full revised roadmap"):
                    st.markdown(plan_to_markdown(pending["plan"], ss.plan_profile, ss.link_results))
                apply_col, discard_col = st.columns(2)
                if apply_col.button("✅ Apply revised roadmap", type="primary", use_container_width=True):
                    progress.apply_pending_revision(ss)
                    refresh_links()
                    st.rerun()
                if discard_col.button("✖ Discard draft", use_container_width=True):
                    progress.discard_pending_revision(ss)
                    st.rerun()

        with st.expander("📝 Revise the roadmap", expanded=False):
            instruction = st.text_area(
                "What should change?",
                key="revision_instruction",
                placeholder="Example: I can only study 5 hours a week from now on. "
                            "Or: replace Week 2's SQL practice with a Power BI exercise.",
            )
            st.caption("Your completed tasks and the coach conversation are sent along. "
                       "Nothing changes until you apply the draft.")
            if st.button("Draft revised roadmap"):
                if client is None:
                    show_client_problem()
                elif not instruction.strip():
                    st.warning("Describe what should change first.")
                else:
                    revision_bar = st.progress(0.0, text="Drafting the revision...")
                    status = st.empty()
                    weeks_expected = ss.roadmap_plan["constraints"]["duration_weeks"]

                    def on_revision_chunk(text):
                        done = stream_progress(text, weeks_expected)
                        revision_bar.progress(done, text=f"Drafting the revision... {round(done * 100)}%")

                    try:
                        hits = rag_system.retrieve(ss, instruction)
                        revision = revise_roadmap(
                            client, ss.roadmap_plan, ss.plan_profile, instruction,
                            settings=settings, history=ss.messages,
                            progress_text=progress.progress_summary_text(ss.tasks), hits=hits,
                            on_chunk=on_revision_chunk,
                            on_reset=lambda: revision_bar.progress(0.0, text="Starting this step again..."),
                            on_status=status.info,
                        )
                    except PlanValidationError as exc:
                        st.error("The drafted revision broke your limits, so it was not kept. "
                                 "Your current roadmap is unchanged.")
                        with st.expander("What was wrong"):
                            for line in exc.errors:
                                st.write(f"- {line}")
                    except (GenerationError, ValueError) as exc:
                        st.error(str(exc))
                    except Exception as exc:  # noqa: BLE001
                        st.error(f"Revision failed: {exc}")
                    else:
                        progress.stage_revision(ss, revision, instruction.strip())
                        st.rerun()
                    finally:
                        revision_bar.empty()
                        status.empty()

        st.divider()
        for message in ss.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                if message.get("sources"):
                    with st.expander(f"Sources: {rag_system.summarize_sources(message['sources'])}"):
                        for hit in message["sources"]:
                            st.markdown(f"**{hit['source']}, p. {hit['page']}**")
                            st.caption(hit["text"])

    question = st.chat_input("Ask about your roadmap...")
    if ss.queued_question:
        question, ss.queued_question = ss.queued_question, None

    if question:
        if not ss.roadmap_plan:
            st.warning("Please generate a roadmap before chatting.")
        elif client is None:
            show_client_problem()
        else:
            with st.chat_message("user"):
                st.markdown(question)
            hits = []
            try:
                hits = rag_system.retrieve(ss, question)
            except Exception as exc:  # noqa: BLE001
                st.warning(f"PDF search was skipped: {exc}")
            llm_messages = prompts.build_chat_messages(
                plan_outline(ss.roadmap_plan),
                progress.progress_summary_text(ss.tasks),
                ss.messages,
                question,
                hits,
            )
            with st.chat_message("assistant"):
                box = st.empty()
                parts = []
                try:
                    for piece in generate_response(client, llm_messages, settings=settings, max_tokens=2000):
                        parts.append(piece)
                        box.markdown("".join(parts) + "▌")
                    answer = "".join(parts).strip()
                    box.markdown(answer)
                    if hits:
                        st.caption("Sources: " + rag_system.summarize_sources(hits))
                    ss.messages = ss.messages + [
                        {"role": "user", "content": question},
                        {"role": "assistant", "content": answer, "sources": hits},
                    ]
                    ss.failed_question = None
                except StreamInterruptedError as exc:
                    box.markdown(exc.partial_text)
                    st.warning("The connection dropped part-way through. This partial answer was "
                               "not saved - retry to get a complete one.")
                    ss.failed_question = question
                except GenerationError as exc:
                    box.empty()
                    st.error(str(exc))
                    ss.failed_question = question

    if ss.failed_question and ss.roadmap_plan:
        if st.button("🔁 Retry last question"):
            ss.queued_question, ss.failed_question = ss.failed_question, None
            st.rerun()

# ==========================================================================
# Tab 3 - Progress Tracker
# ==========================================================================
with tab_progress:
    st.subheader("Track Your Learning Progress")

    with st.expander("💾 Restore saved progress", expanded=not ss.roadmap_plan):
        saved = st.file_uploader("Progress file (JSON exported from this app)", type=["json"], key="progress_upload")
        if st.button("Restore progress", disabled=saved is None):
            try:
                imported = progress.import_progress(saved.getvalue())
            except progress.ProgressImportError as exc:
                st.error(str(exc))
            else:
                progress.load_imported(ss, imported)
                refresh_links()
                ss.flash = "Progress restored." + (
                    f" This roadmap used the PDF **{imported['pdf_filename']}** - upload and index it "
                    "again to use it in the coach." if imported["pdf_filename"] else ""
                )
                st.rerun()

    if ss.get("flash"):
        st.success(ss.flash)
        ss.flash = None

    if not ss.roadmap_plan:
        st.info("Generate a roadmap (or restore saved progress) to start tracking.")
    else:
        stats = progress.progress_stats(ss.tasks)
        st.progress(
            stats["done"] / stats["total"] if stats["total"] else 0.0,
            text=f"{stats['done']} of {stats['total']} tasks done ({stats['percent']}%)",
        )
        st.caption(f"Planned study time completed: {stats['hours_done']:g} of {stats['hours_total']:g} h")

        weeks = sorted({t["week"] for t in ss.tasks if t.get("week") is not None})
        for week in weeks:
            bucket = stats["per_week"][week]
            title = next((w["title"] for w in ss.roadmap_plan["weeks"] if w["week"] == week), "")
            with st.expander(
                f"Week {week}: {title} - {bucket['done']}/{bucket['total']} done",
                expanded=(week == stats["current_week"]),
            ):
                for task in [t for t in ss.tasks if t.get("week") == week]:
                    hours = f" ({task['hours']:g} h)" if task.get("hours") else ""
                    task["done"] = st.checkbox(
                        f"{task['name']}{hours}", value=task["done"],
                        key=f"task_{ss.epoch}_{task['id']}",
                    )

        general = [t for t in ss.tasks if t.get("week") is None]
        if general:
            with st.expander("Your own tasks (not tied to a week)"):
                for task in general:
                    task["done"] = st.checkbox(task["name"], value=task["done"], key=f"task_{ss.epoch}_{task['id']}")

        with st.form("custom_task_form", clear_on_submit=True):
            st.markdown("**Add your own task**")
            name = st.text_input("Task", placeholder="Example: Read the SQLite docs")
            target = st.selectbox("Week", ["No specific week"] + [f"Week {w}" for w in weeks])
            if st.form_submit_button("Add task"):
                week_number = None if target == "No specific week" else int(target.split()[1])
                added, message = progress.add_custom_task(ss.tasks, name, week_number)
                (st.success if added else st.warning)(message)
                if added:
                    st.rerun()

        left, right = st.columns(2)
        left.download_button(
            "⬇️ Export progress (JSON)", data=progress.export_progress(ss),
            file_name="roadmap_progress.json", mime="application/json",
        )
        if right.button("Reset all checkmarks"):
            progress.reset_progress(ss)
            st.rerun()
        st.caption(
            "Progress lives in this browser session. Export it to continue later, then use "
            "**Restore saved progress** above. The coach sees which tasks are done."
        )

# ==========================================================================
# Tab 4 - How it works
# ==========================================================================
with tab_design:
    st.subheader("How the app works")
    st.markdown(
        """
**1. Structured generation.** The model returns the roadmap as JSON (weeks, activities with hours,
milestones, resources, feasibility). The app checks the number of weeks, the hours in every week,
the required sections, and the milestones *before* showing anything. Small hour overruns are fixed
automatically; bigger problems trigger one repair request; a plan that still fails is not shown.

**2. Honest feasibility.** The app looks at your total hours and tells the model when a goal looks
too big. If the goal is not realistic, the plan says what you *can* achieve.

**3. Safe streaming.** A failed request is retried automatically only if no text has appeared yet.
If a stream breaks part-way, the partial output is discarded and the step restarts cleanly, so a
section is never repeated.

**4. One roadmap everywhere.** The displayed plan, the download, the progress tracker and the coach
all read the same stored plan. Chat can *propose* a revision; nothing changes until you press
**Apply revised roadmap**.

**5. PDF knowledge with page references.** An indexed PDF informs roadmap generation, the coach and
revisions. Answers cite page numbers. Removing or replacing the PDF clears the old index.

**6. Verified links.** Every recommended link is requested before it is called verified. Broken or
unconfirmed links are labelled and not clickable.

**7. Progress that feeds back.** Tasks come from the weekly activities and milestones. The coach is
told which are done, and you can export/restore progress between sessions.
"""
    )
    st.code(
        """
Learner profile (+ optional PDF excerpts with page numbers)
        |
        v
prompts.py  ->  Gemini (JSON, streamed, retried only before text appears)
        |
        v
roadmap_engine.py: parse -> normalise -> validate -> (repair once) -> plan
        |
        +--> link_checker.py (verify URLs)
        v
progress.py: plan -> tasks -> coach context / export / revisions
        |
        v
app.py: roadmap tab, coach tab (Apply revised roadmap), progress tab
""",
        language="text",
    )

st.divider()
st.caption("AI Learning Roadmap Generator · Python + Streamlit + Google Gemini + Sentence Transformers + FAISS")
st.caption("Verify resources and adjust the roadmap to your real pace.")

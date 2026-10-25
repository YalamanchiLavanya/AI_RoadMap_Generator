
import streamlit as st
from dotenv import load_dotenv

from roadmap_engine import (
    create_client,
    build_roadmap_prompt,
    build_roadmap_messages,
    generate_response,
    build_chat_messages,
    build_rag_index,
    retrieve_context,
)

load_dotenv()

# -------------------------
# Streamlit Configuration
# -------------------------
st.set_page_config(
    page_title="AI Learning Roadmap Generator",
    page_icon="🧭",
    layout="wide",
)

# -------------------------
# Custom CSS
# -------------------------
st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #f5f7ff, #eef4ff, #f8f5ff);
}
.block-container {
    max-width: 1200px;
    padding-top: 1.5rem;
}
.hero {
    background: linear-gradient(110deg, #172554, #4338ca);
    padding: 28px;
    border-radius: 18px;
    color: white;
    margin-bottom: 20px;
}
.hero h1 {
    color: white;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
    <h1>🧭 AI Learning Roadmap Generator</h1>
    <p>
        Turn your career goal into a personalized weekly learning plan
        with skills, milestones, and resources.
    </p>
</div>
""", unsafe_allow_html=True)

# -------------------------
# Session State
# -------------------------
if "roadmap" not in st.session_state:
    st.session_state.roadmap = ""

if "messages" not in st.session_state:
    st.session_state.messages = []

if "rag_bundle" not in st.session_state:
    st.session_state.rag_bundle = None

if "rag_chunks" not in st.session_state:
    st.session_state.rag_chunks = []

if "tasks" not in st.session_state:
    st.session_state.tasks = []

# -------------------------
# Sidebar: Learner Profile
# -------------------------
with st.sidebar:
    st.header("🎯 Your Learning Profile")

    goal = st.text_input(
        "Career goal",
        value="Become a Data Analyst",
    )

    current_skills = st.text_area(
        "Current skills",
        value="Python basics, Excel basics",
        help="Mention skills you already know.",
    )

    level = st.selectbox(
        "Current skill level",
        ["Beginner", "Intermediate", "Advanced"],
    )

    hours_per_week = st.slider(
        "Study hours per week",
        min_value=2,
        max_value=30,
        value=10,
    )

    duration_weeks = st.slider(
        "Roadmap duration",
        min_value=2,
        max_value=24,
        value=8,
    )

    learning_style = st.selectbox(
        "Preferred learning style",
        [
            "Balanced: theory + practice",
            "Project-based",
            "Video-first",
            "Reading-first",
        ],
    )

    learning_language = st.selectbox(
        "Resource language",
        [
            "English",
            "Telugu + English",
            "Hindi + English",
        ],
    )

    generate_clicked = st.button(
        "✨ Generate My Roadmap",
        type="primary",
        use_container_width=True,
    )

    st.divider()

    st.subheader("📄 Optional PDF Knowledge")

    uploaded_pdf = st.file_uploader(
        "Upload a syllabus or learning guide",
        type=["pdf"],
    )

    index_clicked = st.button(
        "Index PDF for RAG",
        use_container_width=True,
    )

# -------------------------
# Gemini API Client
# -------------------------
@st.cache_resource
def get_llm_client():
    """Create and reuse the configured Gemini API client."""
    return create_client()


client = None
client_error = None

try:
    client = get_llm_client()
except Exception as exc:
    client_error = str(exc)

    st.warning(
        "Gemini is not configured. Check GEMINI_API_KEY "
        "and GEMINI_MODEL in your .env file."
    )

    with st.expander("Configuration details"):
        st.code(client_error)

# -------------------------
# PDF Indexing
# -------------------------
if index_clicked:
    if uploaded_pdf is None:
        st.warning("Please upload a PDF first.")
    else:
        try:
            with st.spinner(
                "Extracting PDF text and creating embeddings..."
            ):
                bundle, chunks = build_rag_index(
                    uploaded_pdf.getvalue()
                )

                st.session_state.rag_bundle = bundle
                st.session_state.rag_chunks = chunks

            st.success(
                f"PDF indexed successfully: {len(chunks)} chunks."
            )

        except Exception as exc:
            st.error(f"PDF processing failed: {exc}")

# -------------------------
# Main Tabs
# -------------------------
tab_roadmap, tab_coach, tab_progress, tab_prompts = st.tabs([
    "🗺️ Roadmap",
    "💬 Roadmap Coach",
    "✅ Progress Tracker",
    "🧠 Prompt Design",
])

# ==================================================
# TAB 1: ROADMAP GENERATOR
# ==================================================
with tab_roadmap:
    st.subheader("Your Personalized Learning Plan")

    st.write(
        "Generate a realistic plan based on your goal, current skills, "
        "available time, and experience."
    )

    if generate_clicked:
        if not goal.strip():
            st.error("Please enter your career goal.")

        elif client is None:
            st.error(
                "The Gemini client is unavailable. "
                "Check your .env configuration."
            )

            if client_error:
                st.code(client_error)

        else:
            try:
                prompt = build_roadmap_prompt(
                    goal=goal.strip(),
                    current_skills=(
                        current_skills.strip() or "Not specified"
                    ),
                    level=level,
                    hours_per_week=hours_per_week,
                    duration_weeks=duration_weeks,
                    learning_style=learning_style,
                    learning_language=learning_language,
                )

                messages = build_roadmap_messages(prompt)

                with st.spinner(
                    "Preparing your personalized learning roadmap..."
                ):
                    answer_parts = []
                    output = st.empty()

                    for piece in generate_response(
                        client,
                        messages,
                        stream=True,
                        max_tokens=3500,
                    ):
                        if piece:
                            answer_parts.append(piece)
                            output.markdown(
                                "".join(answer_parts) + "▌"
                            )

                    answer = "".join(answer_parts).strip()

                if not answer:
                    st.error(
                        "The model returned an empty response. "
                        "Please try again."
                    )
                else:
                    st.session_state.roadmap = answer

                    # Start a fresh chat for the new roadmap.
                    st.session_state.messages = []

                    # Clear tasks from the previous roadmap.
                    st.session_state.tasks = []

                    st.success("Your roadmap is ready!")

            except Exception as exc:
                st.error(f"Roadmap generation failed: {exc}")
                st.info(
                    "Check your internet connection, Gemini API key, "
                    "model name, and API quota."
                )

    if st.session_state.roadmap:
        st.markdown(st.session_state.roadmap)

        st.download_button(
            label="⬇️ Download Roadmap as Markdown",
            data=st.session_state.roadmap,
            file_name="learning_roadmap.md",
            mime="text/markdown",
        )
    else:
        st.info(
            "Fill in your learning profile in the sidebar "
            "and click Generate My Roadmap."
        )

# ==================================================
# TAB 2: ROADMAP COACH
# ==================================================
with tab_coach:
    st.subheader("Chat with Your Roadmap Coach")

    st.write(
        "Ask follow-up questions, request changes, or get help "
        "understanding a topic in your plan."
    )

    if not st.session_state.roadmap:
        st.info(
            "Generate a roadmap first to start a conversation."
        )

    # Display previous conversation.
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    question = st.chat_input("Ask about your roadmap...")

    if question:
        if not st.session_state.roadmap:
            st.warning(
                "Please generate a roadmap before chatting."
            )

        elif client is None:
            st.error(
                "The Gemini client is unavailable. "
                "Check your .env configuration."
            )

            if client_error:
                st.code(client_error)

        else:
            # Save the new question.
            st.session_state.messages.append({
                "role": "user",
                "content": question,
            })

            with st.chat_message("user"):
                st.markdown(question)

            retrieved_context = ""

            # Retrieve relevant PDF content if indexed.
            if st.session_state.rag_bundle is not None:
                try:
                    retrieved_context = retrieve_context(
                        question,
                        st.session_state.rag_bundle,
                        st.session_state.rag_chunks,
                    )
                except Exception as exc:
                    st.warning(
                        f"PDF retrieval was skipped: {exc}"
                    )

            # The current question is passed separately.
            history = st.session_state.messages[:-1]

            messages = build_chat_messages(
                roadmap=st.session_state.roadmap,
                history=history,
                question=question,
                retrieved_context=retrieved_context,
            )

            try:
                with st.chat_message("assistant"):
                    output = st.empty()
                    answer_parts = []

                    for piece in generate_response(
                        client,
                        messages,
                        stream=True,
                        max_tokens=1800,
                    ):
                        if piece:
                            answer_parts.append(piece)
                            output.markdown(
                                "".join(answer_parts) + "▌"
                            )

                    answer = "".join(answer_parts).strip()

                    if answer:
                        output.markdown(answer)

                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": answer,
                        })
                    else:
                        st.error(
                            "No answer was returned. Please try again."
                        )

            except Exception as exc:
                st.error(f"Chat request failed: {exc}")

# ==================================================
# TAB 3: PROGRESS TRACKER
# ==================================================
with tab_progress:
    st.subheader("Track Your Learning Progress")

    st.write(
        "Add learning tasks, mark completed tasks, "
        "and monitor your progress during this session."
    )

    if not st.session_state.roadmap:
        st.info(
            "Generate a roadmap before tracking progress."
        )

    else:
        with st.form("task_form", clear_on_submit=True):
            task_name = st.text_input(
                "Learning task",
                placeholder="Example: Practice SQL joins",
            )

            submitted = st.form_submit_button("Add Task")

        if submitted:
            clean_task_name = task_name.strip()

            if not clean_task_name:
                st.warning("Enter a task name.")

            elif any(
                task["name"].casefold() == clean_task_name.casefold()
                for task in st.session_state.tasks
            ):
                st.warning("This task already exists.")

            else:
                st.session_state.tasks.append({
                    "name": clean_task_name,
                    "done": False,
                })
                st.rerun()

        if st.session_state.tasks:
            for index, task in enumerate(st.session_state.tasks):
                task["done"] = st.checkbox(
                    task["name"],
                    value=task["done"],
                    key=f"task_{index}_{task['name']}",
                )

            completed = sum(
                task["done"] for task in st.session_state.tasks
            )
            total = len(st.session_state.tasks)
            percentage = round(completed / total * 100)

            st.progress(
                completed / total,
                text=(
                    f"{completed} of {total} tasks completed "
                    f"({percentage}%)"
                ),
            )

            if st.button("Clear All Tasks"):
                st.session_state.tasks = []
                st.rerun()

        else:
            st.info(
                "No tasks yet. Add your first learning task above."
            )

        st.caption(
            "Progress is stored in the active Streamlit session. "
            "It is not permanently saved to a database."
        )

# ==================================================
# TAB 4: PROMPT ENGINEERING
# ==================================================
with tab_prompts:
    st.subheader("Prompt Engineering Demonstration")

    st.markdown("""
### 1. Role-Based Prompting

The system prompt defines the model as an expert learning roadmap
coach and sets expectations for answer quality.

### 2. Few-Shot Prompting

The prompt includes a short example roadmap to demonstrate the
expected weekly structure and level of detail.

### 3. Stepwise Planning

The prompt asks the model to identify skill gaps, sequence
prerequisites, allocate time, and define milestones. It requests
a concise planning rationale rather than private hidden chain-of-thought.

### 4. Structured Output

The model is asked to return predictable Markdown sections for
the learner profile, skill gaps, weekly plan, capstone, and checkpoints.

### 5. Conversation Memory

The Roadmap Coach receives the current roadmap and recent
conversation history so follow-up requests can refine the plan.

### 6. Retrieval Augmented Generation (RAG)

An uploaded PDF is split into chunks, converted into embeddings,
and indexed with FAISS. Relevant excerpts are retrieved and added
to the question sent to the LLM.
""")

    st.markdown("### Processing Flow")

    st.code("""
Learner profile
      |
      v
System prompt + user prompt + few-shot example
      |
      +----------------------------+
      |                            |
      v                            v
Gemini roadmap generation    Optional PDF RAG
                                  |
                          Text chunks and embeddings
                                  |
                            FAISS retrieval
                                  |
      +---------------------------+
      |
      v
Google Gemini API
      |
      v
Streaming response in Streamlit
      |
      v
Roadmap, coach, and progress tracking
""", language="text")

# -------------------------
# Footer
# -------------------------
st.divider()

st.caption(
    "AI Learning Roadmap Generator | Python + Streamlit + "
    "Google Gemini + Sentence Transformers + FAISS"
)

st.caption(
    "Verify resource recommendations and adjust the roadmap "
    "to your actual learning pace."
)

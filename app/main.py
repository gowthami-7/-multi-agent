
import json
from datetime import datetime

import streamlit as st

from core.orchestrator import run_workflow


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="AgentFlow AI",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# SOFT SAGE GREEN THEME
# ============================================================

st.markdown(
    """
    <style>
    :root {
        --sage: #527D5C;
        --sage-dark: #416749;
        --sage-light: #DCEBDD;
        --text: #294735;
        --muted: #6F8975;
        --border: #D5E3D5;
        --surface: #FFFFFF;
        --background: #F1F6F0;
    }

    .stApp {
        background: linear-gradient(135deg, #F1F6F0, #E8F0E6);
        color: var(--text);
    }

    [data-testid="stHeader"] {
        background: rgba(241, 246, 240, 0.95);
    }

    [data-testid="stSidebar"] {
        background: #E5EEE2;
        border-right: 1px solid var(--border);
    }

    [data-testid="stSidebar"] * {
        color: var(--text);
    }

    h1, h2, h3, h4, p, label {
        color: var(--text);
    }

    [data-testid="stCaptionContainer"] {
        color: var(--muted);
    }

    [data-testid="stMetric"] {
        background: var(--surface);
        border: 1px solid var(--border);
        padding: 18px;
        border-radius: 14px;
        box-shadow: 0 3px 12px rgba(56, 85, 60, 0.05);
    }

    [data-testid="stMetricLabel"] {
        color: var(--muted);
    }

    [data-testid="stMetricValue"] {
        color: var(--sage);
    }

    .stButton > button,
    .stDownloadButton > button {
        background: var(--sage);
        color: white;
        border: 1px solid var(--sage);
        border-radius: 10px;
        font-weight: 600;
        transition: 0.2s ease;
    }

    .stButton > button:hover,
    .stDownloadButton > button:hover {
        background: var(--sage-dark);
        border-color: var(--sage-dark);
        color: white;
    }

    .stTextArea textarea,
    .stTextInput input,
    .stNumberInput input {
        background: white;
        color: var(--text);
        border: 1px solid #C9DCC8;
        border-radius: 10px;
    }

    [data-testid="stExpander"] {
        background: white;
        border: 1px solid var(--border);
        border-radius: 12px;
    }

    [data-testid="stTabs"] button {
        color: var(--muted);
    }

    [data-testid="stTabs"] button[aria-selected="true"] {
        color: var(--sage-dark);
        border-bottom-color: var(--sage);
    }

    [data-testid="stAlert"] {
        border-radius: 10px;
    }

    hr {
        border-color: var(--border);
    }

    .hero {
        padding: 24px;
        background: rgba(255, 255, 255, 0.85);
        border: 1px solid var(--border);
        border-radius: 18px;
        margin-bottom: 20px;
    }

    .hero-label {
        color: var(--sage);
        font-size: 13px;
        font-weight: 700;
        letter-spacing: 2px;
        text-transform: uppercase;
    }

    .hero-title {
        color: var(--text);
        font-size: 36px;
        font-weight: 750;
        margin: 8px 0;
    }

    .hero-subtitle {
        color: var(--muted);
        font-size: 16px;
        line-height: 1.6;
    }

    .agent-card {
        background: white;
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 16px;
        min-height: 120px;
    }

    .agent-name {
        font-size: 16px;
        font-weight: 700;
        color: var(--text);
    }

    .agent-description {
        font-size: 13px;
        color: var(--muted);
        margin-top: 6px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# HELPERS
# ============================================================

def to_plain_data(value):
    """Convert workflow data into JSON-serializable values."""
    if hasattr(value, "__dict__"):
        return {
            key: to_plain_data(item)
            for key, item in vars(value).items()
        }

    if isinstance(value, dict):
        return {
            str(key): to_plain_data(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [to_plain_data(item) for item in value]

    if isinstance(value, (str, int, float, bool)) or value is None:
        return value

    return str(value)


def get_value(state, name, default=None):
    """Safely read a field from the workflow state."""
    if isinstance(state, dict):
        return state.get(name, default)

    return getattr(state, name, default)


def status_label(status):
    """Create a readable workflow status label."""
    status = str(status or "unknown")
    return status.replace("_", " ").replace("-", " ").title()


def display_json(value):
    st.json(to_plain_data(value))


# ============================================================
# SESSION STATE
# ============================================================

if "workflow_state" not in st.session_state:
    st.session_state.workflow_state = None

if "last_request" not in st.session_state:
    st.session_state.last_request = ""

if "last_run_time" not in st.session_state:
    st.session_state.last_run_time = None


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.markdown("## 🌿 AgentFlow AI")
    st.caption("Multi-agent task automation")

    st.divider()

    st.markdown("### How it works")

    st.markdown(
        """
        **🧭 Planner Agent**  
        Breaks your goal into tasks.

        **🔎 Researcher Agent**  
        Retrieves information and evidence.

        **⚙️ Executor Agent**  
        Performs the planned tasks.

        **✅ Verifier Agent**  
        Reviews results and checks requirements.
        """
    )

    st.divider()

    st.markdown("### Workflow settings")

    max_retries = st.number_input(
        "Maximum execution retries",
        min_value=0,
        max_value=5,
        value=2,
        step=1,
        help="Retry limit configured in the dashboard.",
    )

    st.caption(
        "Use a clear, specific task for the best results."
    )


# ============================================================
# HERO SECTION
# ============================================================

st.markdown(
    """
    <div class="hero">
        <div class="hero-label">Intelligent workflow automation</div>
        <div class="hero-title">🌿 AgentFlow AI</div>
        <div class="hero-subtitle">
            Turn a goal into an organized workflow using
            collaborating agents. Plan, research, execute,
            and verify tasks in one place.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("### Four agents. One workflow.")

agent_columns = st.columns(4)

agents = [
    (
        "🧭",
        "Planner Agent",
        "Breaks your request into actionable tasks.",
    ),
    (
        "🔎",
        "Researcher Agent",
        "Finds relevant information and evidence.",
    ),
    (
        "⚙️",
        "Executor Agent",
        "Carries out the planned tasks.",
    ),
    (
        "✅",
        "Verifier Agent",
        "Reviews outputs and checks requirements.",
    ),
]

for column, (emoji, name, description) in zip(
    agent_columns, agents
):
    with column:
        st.markdown(
            f"""
            <div class="agent-card">
                <div style="font-size:26px">{emoji}</div>
                <div class="agent-name">{name}</div>
                <div class="agent-description">{description}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.divider()


# ============================================================
# TASK INPUT
# ============================================================

st.markdown("### What would you like the agents to accomplish?")

with st.form("workflow_form"):
    user_request = st.text_area(
        "Your task",
        value=st.session_state.last_request,
        height=150,
        placeholder=(
            "Example: Calculate the total cost of 5 notebooks "
            "at ₹40 each and 3 pens at ₹10 each, then verify "
            "the calculation."
        ),
    )

    submitted = st.form_submit_button(
        "▶ Run workflow",
        type="primary",
        width="stretch",
    )

if submitted:
    if not user_request.strip():
        st.warning("Please enter a task before starting.")
    else:
        try:
            with st.spinner(
                "Agents are planning, executing and verifying..."
            ):
                # Run the existing workflow engine.
                # Retry settings remain controlled by the
                # workflow engine unless its API supports overrides.
                result = run_workflow(user_request.strip())

            st.session_state.workflow_state = result
            st.session_state.last_request = user_request.strip()
            st.session_state.last_run_time = datetime.now().strftime(
                "%d %b %Y, %I:%M:%S %p"
            )

            st.success(
                "Workflow run finished. Check each result below."
            )

        except Exception as exc:
            st.error("The workflow could not be completed.")
            st.exception(exc)


# ============================================================
# WORKFLOW RESULTS
# ============================================================

state = st.session_state.workflow_state

if state is not None:
    st.divider()
    st.markdown("## Workflow results")

    status = get_value(state, "workflow_status", "unknown")
    tasks = get_value(state, "tasks", []) or []
    executions = get_value(state, "execution_results", []) or []
    errors = get_value(state, "errors", []) or []
    research = get_value(state, "research_results", []) or []
    verifications = get_value(state, "verification_results", []) or []
    logs = get_value(state, "workflow_log", []) or []
    final_result = get_value(state, "final_result", None)

    latest_verification = (
        verifications[-1] if verifications else {}
    )

    if not isinstance(latest_verification, dict):
        latest_verification = to_plain_data(latest_verification)
        if not isinstance(latest_verification, dict):
            latest_verification = {}

    passed = latest_verification.get("passed")
    score = latest_verification.get("score")

    metric_columns = st.columns(4)

    metric_columns[0].metric(
        "Workflow status",
        status_label(status),
    )

    metric_columns[1].metric(
        "Tasks planned",
        len(tasks),
    )

    metric_columns[2].metric(
        "Execution records",
        len(executions),
    )

    metric_columns[3].metric(
        "Errors recorded",
        len(errors),
    )

    if passed is True:
        st.success(
            f"Verification passed"
            + (f" — {score}/100" if score is not None else "")
        )
    elif passed is False:
        st.warning(
            f"Verification did not pass"
            + (f" — {score}/100" if score is not None else "")
        )
    else:
        st.info(
            "The workflow did not provide a final verification result."
        )

    if st.session_state.last_run_time:
        st.caption(
            f"Last run: {st.session_state.last_run_time}"
        )

    overview_tab, tasks_tab, research_tab, activity_tab = st.tabs(
        [
            "📊 Overview",
            "🗂 Tasks & execution",
            "🔍 Research & verification",
            "📜 Activity & errors",
        ]
    )

    # --------------------------------------------------------
    # OVERVIEW
    # --------------------------------------------------------

    with overview_tab:
        st.markdown("### Original request")
        st.write(
            get_value(state, "user_request", "")
        )

        st.markdown("### Final workflow result")

        if final_result:
            if isinstance(final_result, (dict, list)):
                display_json(final_result)
            else:
                st.write(final_result)
        else:
            st.caption(
                "No separate final result was provided by the workflow."
            )

        if latest_verification:
            st.markdown("### Verification summary")
            st.write(
                latest_verification.get(
                    "summary",
                    "No verification summary is available.",
                )
            )

            method = latest_verification.get(
                "verification_method"
            )

            if method:
                st.caption(f"Verification method: {method}")

            st.caption(
                "A passing verification result reflects the checks "
                "performed by this system; it is not automatically "
                "proof of independent fact-checking."
            )

        report = {
            "project": "AgentFlow AI",
            "generated_at": datetime.now().isoformat(
                timespec="seconds"
            ),
            "original_request": get_value(
                state, "user_request", ""
            ),
            "workflow_status": status,
            "tasks": to_plain_data(tasks),
            "execution_results": to_plain_data(executions),
            "research_results": to_plain_data(research),
            "verification_results": to_plain_data(verifications),
            "errors": to_plain_data(errors),
            "workflow_log": to_plain_data(logs),
            "final_result": to_plain_data(final_result),
        }

        st.download_button(
            label="📥 Download workflow report (JSON)",
            data=json.dumps(
                report,
                ensure_ascii=False,
                indent=2,
            ),
            file_name="agentflow_workflow_report.json",
            mime="application/json",
            width="stretch",
        )

    # --------------------------------------------------------
    # TASKS AND EXECUTION
    # --------------------------------------------------------

    with tasks_tab:
        st.markdown("### Planned tasks")

        if tasks:
            for index, task in enumerate(tasks, start=1):
                with st.expander(
                    f"Task {index}",
                    expanded=(index == 1),
                ):
                    display_json(task)
        else:
            st.info("No planned tasks were recorded.")

        st.markdown("### All execution records")

        if executions:
            for index, execution in enumerate(
                executions, start=1
            ):
                with st.expander(
                    f"Execution record {index}"
                ):
                    display_json(execution)
        else:
            st.info("No execution records were recorded.")

    # --------------------------------------------------------
    # RESEARCH AND VERIFICATION
    # --------------------------------------------------------

    with research_tab:
        st.markdown("### Research findings")

        if research:
            for index, item in enumerate(research, start=1):
                with st.expander(
                    f"Research task {index}",
                    expanded=True,
                ):
                    display_json(item)
        else:
            st.info(
                "This workflow did not record separate research results."
            )

        st.markdown("### Verification details")

        if verifications:
            for index, verification in enumerate(
                verifications, start=1
            ):
                with st.expander(
                    f"Verification record {index}",
                    expanded=True,
                ):
                    display_json(verification)
        else:
            st.info(
                "No verification records were returned."
            )

    # --------------------------------------------------------
    # ACTIVITY AND ERRORS
    # --------------------------------------------------------

    with activity_tab:
        st.markdown("### Workflow activity")

        if logs:
            for entry in logs:
                st.write(f"• {entry}")
        else:
            st.info("No workflow log entries were recorded.")

        st.markdown("### Errors and warnings")

        if errors:
            for index, error in enumerate(errors, start=1):
                st.warning(f"{index}. {error}")
        else:
            st.success("No errors were recorded for this workflow.")

    st.divider()
    st.caption(
        "AgentFlow AI · Multi-agent workflow dashboard"
    )

else:
    st.info(
        "Start a workflow above to view task execution, "
        "research evidence, verification results and activity logs."
    )

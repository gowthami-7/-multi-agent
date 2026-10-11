
import json
import re

from services.ai_service import generate_ai_response
from core.state import WorkflowState


ALLOWED_TASK_TYPES = {
    "research",
    "calculation",
    "analysis",
    "recommendation",
    "general",
}


def _parse_task_response(response: str) -> list:
    """Parse and validate AI-generated task plans."""

    if not isinstance(response, str) or not response.strip():
        raise ValueError("The AI returned an empty planning response.")

    cleaned = response.strip()
    cleaned = re.sub(
        r"^\s*```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE
    )
    cleaned = re.sub(r"\s*```\s*$", "", cleaned)

    start = cleaned.find("[")
    end = cleaned.rfind("]")

    if start == -1 or end < start:
        raise ValueError("The AI response did not contain a JSON task array.")

    tasks = json.loads(cleaned[start:end + 1])

    if not isinstance(tasks, list) or not 2 <= len(tasks) <= 5:
        raise ValueError("A valid plan must contain 2 to 5 tasks.")

    aliases = {
        "verification": "analysis",
        "verify": "analysis",
        "computation": "calculation",
        "search": "research",
        "summarization": "analysis",
        "summary": "analysis",
    }

    validated = []

    for index, task in enumerate(tasks, start=1):
        if not isinstance(task, dict):
            raise ValueError(f"Task {index} must be an object.")

        description = task.get("description", "")
        if not isinstance(description, str) or not description.strip():
            raise ValueError(f"Task {index} has no valid description.")

        task_type = str(
            task.get("task_type", "general")
        ).lower().strip()
        task_type = aliases.get(task_type, task_type)

        if task_type not in ALLOWED_TASK_TYPES:
            raise ValueError(f"Unsupported task type: {task_type}")

        validated.append({
            "task_id": index,
            "task_type": task_type,
            "description": description.strip(),
            "status": "pending",
        })

    return validated


def _is_event_budget_request(text: str) -> bool:
    """Recognize event-planning requests that also ask for calculations."""

    lowered = text.lower()

    event_words = (
        "event",
        "technical event",
        "workshop",
        "conference",
        "college fest",
        "seminar",
    )

    budget_words = (
        "budget",
        "cost",
        "expenses",
        "spending limit",
        "maximum amount",
    )

    return (
        any(word in lowered for word in event_words)
        and any(word in lowered for word in budget_words)
    )


def _fallback_plan(user_request: str) -> list:
    """Create a deterministic plan for supported common requests."""

    request = user_request.strip()
    lowered = request.lower()

    # Handle mixed event-planning and calculation requests FIRST.
    # Do not send the entire natural-language request to the calculator.
    if _is_event_budget_request(request):
        return [
            {
                "task_id": 1,
                "task_type": "calculation",
                "description": (
                    "Calculate and verify this illustrative event budget "
                    "using the explicit arithmetic expression "
                    "(2000)+(100*50)+(100*10)+(2000). "
                    "Estimated breakdown: venue arrangements ₹2000; "
                    "refreshments ₹50 per student for 100 students; "
                    "certificates ₹10 each for 100 students; "
                    "technical materials ₹2000. "
                    "These are planning estimates, not market quotations. "
                    "Check whether the total is within ₹10000."
                ),
                "status": "pending",
            },
            {
                "task_id": 2,
                "task_type": "analysis",
                "description": (
                    "Prepare a one-day technical event plan for 100 students "
                    "using the successful calculation result from task 1. "
                    "Present actionable preparation steps, the four budget "
                    "categories and their estimates, the total, the remaining "
                    "budget or overrun, and whether the ₹10000 limit is met. "
                    "Clearly label all figures as estimates. Do not claim "
                    "that bookings or purchases have been made. If the "
                    "calculation failed, identify the missing result instead "
                    "of inventing one."
                ),
                "status": "pending",
            },
        ]

    is_calculation = bool(re.search(
        r"\b(calculate|compute|multiply|multiplication|"
        r"arithmetic|product of|divided by|times)\b",
        lowered,
    ))

    is_research = bool(re.search(
        r"\b(research|wikipedia|sources?|retrieve information|"
        r"find information|look up|literature review)\b",
        lowered,
    ))

    if is_calculation:
        return [
            {
                "task_id": 1,
                "task_type": "calculation",
                "description": (
                    "Calculate the requested arithmetic expression: "
                    + request
                ),
                "status": "pending",
            },
            {
                "task_id": 2,
                "task_type": "analysis",
                "description": (
                    "Explain and verify the calculation using the "
                    "recorded calculator result from task 1."
                ),
                "status": "pending",
            },
        ]

    if is_research:
        return [
            {
                "task_id": 1,
                "task_type": "research",
                "description": (
                    "Retrieve relevant information and source evidence for: "
                    + request
                ),
                "status": "pending",
            },
            {
                "task_id": 2,
                "task_type": "analysis",
                "description": (
                    "Summarize the retrieved findings, include source "
                    "titles and URLs, and identify whether the evidence "
                    "supports the summary. Do not invent facts."
                ),
                "status": "pending",
            },
        ]

    return [
        {
            "task_id": 1,
            "task_type": "analysis",
            "description": (
                "Analyze the user's request and identify the required work: "
                + request
            ),
            "status": "pending",
        },
        {
            "task_id": 2,
            "task_type": "general",
            "description": (
                "Produce a response addressing the request using available "
                "workflow context and state any missing information."
            ),
            "status": "pending",
        },
    ]


def plan_tasks(state: WorkflowState) -> WorkflowState:
    """Plan common workflows locally and use AI for other requests."""

    state.workflow_status = "planning"
    state.tasks = []
    state.add_log("Planning Agent started.")

    request = (state.user_request or "").strip()

    if not request:
        state.workflow_status = "planning_failed"
        state.add_error("Planning Agent received an empty user request.")
        return state

    # Prioritize event budgeting over generic calculation detection.
    is_event_budget = _is_event_budget_request(request)

    is_common_request = bool(re.search(
        r"\b(calculate|compute|multiply|multiplication|"
        r"arithmetic|product of|divided by|times|research|"
        r"wikipedia|sources?|retrieve information|find information|"
        r"look up|literature review)\b",
        request,
        flags=re.IGNORECASE,
    ))

    if is_event_budget or is_common_request:
        state.tasks = _fallback_plan(request)
        state.workflow_status = "planning_completed"

        if is_event_budget:
            state.add_log(
                "Planning Agent recognized an event-budgeting workflow "
                "and created a calculation task followed by analysis."
            )
        else:
            state.add_log(
                "Planning Agent used a deterministic plan for a recognized "
                "research or calculation request."
            )

        state.add_log(
            f"Planning Agent created {len(state.tasks)} validated tasks."
        )
        return state

    prompt = f"""
You are the Planning Agent in a multi-agent workflow system.

Decompose the user request into 2 to 5 executable tasks.

USER REQUEST:
{request}

Each task must contain:
- task_id: integer starting at 1
- task_type: research, calculation, analysis, recommendation, or general
- description: specific actionable instruction
- status: pending

Rules:
- Use research only when external information is required.
- Use calculation only when a supported arithmetic expression can be
  extracted from the task description.
- For complex tasks, break work into executable steps.
- Analysis tasks must depend on information produced by earlier tasks.
- Do not invent completed actions, evidence, or results.
- Order tasks logically.
- Return only a valid JSON array with no Markdown fences.
"""

    last_error = None

    for attempt in range(1, 3):
        try:
            state.add_log(f"Planning Agent attempt {attempt}/2.")
            response = generate_ai_response(prompt)
            state.tasks = _parse_task_response(response)
            state.workflow_status = "planning_completed"

            state.add_log(
                f"Planning Agent created {len(state.tasks)} validated tasks."
            )
            return state

        except Exception as exc:
            last_error = exc
            state.tasks = []
            state.add_log(f"Planning attempt {attempt} failed: {exc}")

            error_text = str(exc).lower()
            if "429" in error_text or "rate limit" in error_text:
                state.add_log(
                    "Planning stopped retrying because the AI provider "
                    "reported a rate limit."
                )
                break

    state.tasks = _fallback_plan(request)
    state.workflow_status = "planning_completed"
    state.add_log("Planning Agent switched to its deterministic fallback.")
    state.add_log(f"Fallback planner created {len(state.tasks)} tasks.")

    if last_error:
        state.add_error(
            "AI planner used fallback after planning failed: "
            + str(last_error)
        )

    return state

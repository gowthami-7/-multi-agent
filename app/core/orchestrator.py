
from core.state import WorkflowState
from agents.planner import plan_tasks
from agents.researcher import research_task
from agents.executor import execute_task
from agents.verifier import verify_workflow


def _get_task_type(task):
    """Return a normalized task type."""
    return str(
        task.get("task_type", task.get("type", "general"))
    ).strip().lower()


def _record_text(record):
    """Combine error details for failure classification."""
    if not isinstance(record, dict):
        return ""

    tool_result = record.get("tool_result") or {}

    parts = [
        record.get("error"),
        record.get("output"),
        tool_result.get("error"),
    ]

    return " ".join(
        str(part) for part in parts if part
    ).strip().lower()


def _is_non_retryable_failure(task_type, record):
    """
    Identify known failures that repeating the same task cannot fix.

    Unknown failures remain eligible for the configured retry policy.
    """
    text = _record_text(record)

    if task_type in {"calculation", "calculator", "math"}:
        return (
            "division by zero" in text
            or "division by zero is undefined" in text
        ) and (
            "undefined" in text
            or "no numerical result exists" in text
        )

    if task_type == "analysis":
        return (
            "analysis blocked" in text
            and (
                "required calculation failed" in text
                or "prerequisite failed" in text
            )
        )

    return False


def _run_research(state, task):
    """Run research and normalize its execution record."""
    result = research_task(state, task)

    record = {
        "task_id": result.get(
            "task_id", task.get("task_id", task.get("id"))
        ),
        "task_type": "research",
        "description": task.get("description", ""),
        "success": bool(result.get("success")),
        "output": result.get("findings", ""),
        "tool_result": {
            "success": bool(result.get("success")),
            "query": result.get("query", ""),
            "results": result.get("sources", []),
            "error": result.get("error"),
        },
        "fallback_used": True,
        "error": result.get("error"),
    }

    state.execution_results.append(record)
    return record


def run_workflow(user_input: str, max_retries: int = 2):
    """Plan, execute, and verify a workflow."""

    state = WorkflowState(
        user_request=str(user_input or "").strip(),
        max_retries=max(0, min(int(max_retries), 5)),
    )

    if not state.user_request:
        state.add_error(
            "Please enter a task before running the workflow."
        )
        state.workflow_status = "failed"
        return state

    state.workflow_status = "planning"
    state.add_log("Workflow started.")
    state.add_log("Planning Agent is creating the task plan.")

    try:
        plan_tasks(state)
    except Exception as exc:
        state.add_error(f"Planning Agent failed: {exc}")
        state.workflow_status = "failed"
        return state

    tasks = list(state.tasks)

    if not tasks:
        state.add_error(
            "The Planning Agent did not create any tasks."
        )
        state.workflow_status = "failed"
        return state

    state.add_log(
        f"Workflow plan contains {len(tasks)} task(s)."
    )
    state.workflow_status = "running"

    for index, task in enumerate(tasks):
        state.current_task_index = index
        task_type = _get_task_type(task)
        task_id = task.get("task_id", task.get("id", index + 1))

        state.reset_retry_count()
        attempt_number = 0
        attempt_record = None

        while True:
            attempt_number += 1
            state.add_log(
                f"Starting task {task_id}, attempt {attempt_number}."
            )

            try:
                if task_type == "research":
                    attempt_record = _run_research(state, task)
                else:
                    attempt_record = execute_task(state, task)

                    if not isinstance(attempt_record, dict):
                        attempt_record = {
                            "task_id": task_id,
                            "task_type": task_type,
                            "description": task.get("description", ""),
                            "success": False,
                            "output": (
                                "Executor returned an invalid result."
                            ),
                            "error": "Invalid executor result format.",
                        }

                    state.execution_results.append(attempt_record)

                attempt_record.setdefault("task_id", task_id)
                attempt_record.setdefault("task_type", task_type)
                attempt_record.setdefault(
                    "description", task.get("description", "")
                )

            except Exception as exc:
                attempt_record = {
                    "task_id": task_id,
                    "task_type": task_type,
                    "description": task.get("description", ""),
                    "success": False,
                    "output": f"Task execution failed: {exc}",
                    "tool_result": None,
                    "fallback_used": False,
                    "error": str(exc),
                }
                state.execution_results.append(attempt_record)
                state.add_log(
                    f"Task {task_id} raised an execution exception."
                )

            if attempt_record.get("success") is True:
                state.add_log(
                    f"Task {task_id} completed successfully."
                )
                state.reset_retry_count()
                break

            error = (
                attempt_record.get("error")
                or "The agent did not report a successful result."
            )

            # Do not repeat known deterministic failures.
            if _is_non_retryable_failure(task_type, attempt_record):
                state.add_log(
                    f"Task {task_id} has a non-retryable failure. "
                    f"Stopping retries. Reason: {error}"
                )
                state.add_error(
                    f"Task {task_id} could not complete: {error}"
                )
                break

            if state.can_retry():
                state.increment_retry()
                state.add_log(
                    f"Task {task_id} failed. Retrying "
                    f"({state.retry_count}/{state.max_retries}). "
                    f"Reason: {error}"
                )
                continue

            state.add_error(
                f"Task {task_id} failed after "
                f"{attempt_number} attempt(s): {error}"
            )
            break

    state.final_result = "\n\n".join(
        str(item.get("output", ""))
        for item in state.execution_results
        if item.get("output")
    )

    state.add_log("All planned tasks have been processed.")
    state.add_log("Verification Agent is checking the workflow.")

    try:
        verification = verify_workflow(state)

        if not isinstance(verification, dict):
            state.add_error(
                "Verification Agent returned an unexpected result."
            )
            state.workflow_status = "verification_failed"

    except Exception as exc:
        state.add_error(
            f"Verification Agent failed: {exc}"
        )
        state.workflow_status = "verification_failed"

    state.add_log(
        f"Workflow finished with status: {state.workflow_status}."
    )

    return state

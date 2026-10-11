
import re

from core.state import WorkflowState
from tools.calculator import calculate


def _task_id(item):
    """Read task IDs consistently across workflow records."""
    return str(item.get("task_id", item.get("id", "unknown")))


def _task_type(task):
    """Normalize task types."""
    return str(
        task.get("task_type", task.get("type", "general"))
    ).strip().lower()


def _successful_execution(task_id, executions):
    """Return the latest successful execution for a task."""
    return next(
        (
            item for item in reversed(executions)
            if _task_id(item) == str(task_id)
            and item.get("success") is True
        ),
        None,
    )


def _latest_execution(task_id, executions):
    """Return the latest execution, including failed attempts."""
    return next(
        (
            item for item in reversed(executions)
            if _task_id(item) == str(task_id)
        ),
        None,
    )


def _record_text(record):
    """Collect error and output text for safe error classification."""
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


def _is_safe_division_by_zero(record):
    """
    Recognize the calculator's explicit division-by-zero rejection.

    This does not accept arbitrary failed calculations as safe.
    """
    text = _record_text(record)

    return (
        "division by zero" in text
        or "division by zero is undefined" in text
    ) and (
        "undefined" in text
        or "no numerical result exists" in text
    )


def _is_blocked_analysis(record):
    """Recognize analysis explicitly blocked by a failed prerequisite."""
    text = _record_text(record)

    return (
        "analysis blocked" in text
        and (
            "required calculation failed" in text
            or "prerequisite failed" in text
        )
    )


def _valid_sources(research):
    """Keep sources with a title and a valid HTTP(S) URL."""
    usable = []

    for source in research.get("sources") or []:
        if not isinstance(source, dict):
            continue

        title = str(source.get("title") or "").strip()
        url = str(source.get("url") or "").strip()
        snippet = str(source.get("snippet") or "").strip()

        if title and re.match(r"^https?://\S+$", url):
            usable.append({
                "title": title,
                "url": url,
                "snippet": snippet,
            })

    return usable


def _numbers_match(recorded_value, recomputed_value):
    """Compare numerical results safely."""
    try:
        return abs(
            float(recorded_value) - float(recomputed_value)
        ) <= 1e-9
    except (TypeError, ValueError, OverflowError):
        return False


def verify_workflow(state: WorkflowState) -> dict:
    """
    Verify execution, research evidence, and calculation consistency.

    Expected division-by-zero rejection counts as safely handled when
    the calculator explicitly reports that no numerical result exists.
    Analysis blocked by that failed prerequisite is also recognized.

    Research checks are structural; they do not independently fact-check
    the truth of research claims.
    """
    state.workflow_status = "verifying"
    state.add_log("Verification Agent started.")

    checks = []
    issues = []
    sources = []
    checked_calculations = 0
    checked_research = 0
    safe_rejections = 0
    safely_blocked_tasks = 0

    tasks = getattr(state, "tasks", []) or []
    executions = getattr(state, "execution_results", []) or []
    research_results = getattr(state, "research_results", []) or []

    if not tasks:
        issues.append("The Planner did not create any tasks.")

    execution_by_id = {}

    # Verify every planned task.
    for task in tasks:
        task_id = _task_id(task)
        task_type = _task_type(task)

        execution = _successful_execution(task_id, executions)
        latest = _latest_execution(task_id, executions)

        check = {
            "task_id": task_id,
            "task_type": task_type,
            "execution_success": execution is not None,
            "safe_rejection": False,
            "blocked_safely": False,
            "research_success": None,
        }

        if execution is None:
            # A division-by-zero request should be rejected safely,
            # not mistaken for a successful numerical calculation.
            if (
                task_type in {"calculation", "calculator", "math"}
                and latest is not None
                and _is_safe_division_by_zero(latest)
            ):
                check["safe_rejection"] = True
                safe_rejections += 1
                checks.append(check)
                state.add_log(
                    f"Task {task_id}: expected division-by-zero "
                    "rejection verified; no numerical result accepted."
                )
                continue

            # Do not report an explicitly blocked dependent analysis
            # as an unexpected software failure.
            if (
                task_type == "analysis"
                and latest is not None
                and _is_blocked_analysis(latest)
            ):
                check["blocked_safely"] = True
                safely_blocked_tasks += 1
                checks.append(check)
                state.add_log(
                    f"Task {task_id}: analysis was safely blocked "
                    "because its prerequisite failed."
                )
                continue

            issues.append(
                f"Task {task_id} has no successful execution "
                "or recognized safe rejection."
            )
            checks.append(check)
            continue

        execution_by_id[task_id] = execution

        output = str(execution.get("output") or "").strip()

        if not output:
            issues.append(f"Task {task_id} has empty output.")

        # Verify research records and their supporting sources.
        if task_type == "research":
            checked_research += 1

            matching_research = [
                item for item in research_results
                if str(
                    item.get("task_id", item.get("id", "unknown"))
                ) == task_id
            ]

            research = next(
                (
                    item for item in reversed(matching_research)
                    if item.get("success") is True
                ),
                None,
            )

            findings = ""
            usable_sources = []

            if research:
                findings = str(
                    research.get("findings") or ""
                ).strip()
                usable_sources = _valid_sources(research)

            research_ok = bool(
                research and findings and usable_sources
            )
            check["research_success"] = research_ok

            if not research:
                issues.append(
                    f"Research task {task_id} has no successful "
                    "research record."
                )
            elif not findings:
                issues.append(
                    f"Research task {task_id} has no stored findings."
                )

            if not usable_sources:
                issues.append(
                    f"Research task {task_id} has no sources with "
                    "valid titles and URLs."
                )
            else:
                sources.extend(usable_sources)

            if findings and findings not in output:
                issues.append(
                    f"Research task {task_id} output does not include "
                    "its stored findings."
                )

        # Independently recalculate successful calculation tasks.
        elif task_type in {"calculation", "calculator", "math"}:
            tool_result = execution.get("tool_result") or {}

            if not tool_result.get("success"):
                issues.append(
                    f"Calculation task {task_id} has no successful "
                    "calculator result."
                )
            else:
                expression = tool_result.get("expression")
                recorded_value = tool_result.get("result")

                if expression is None or recorded_value is None:
                    issues.append(
                        f"Calculation task {task_id} is missing its "
                        "expression or result."
                    )
                else:
                    recomputed = calculate(str(expression))

                    if not recomputed.get("success"):
                        issues.append(
                            f"Calculation task {task_id} could not "
                            "be recalculated."
                        )
                    elif _numbers_match(
                        recorded_value, recomputed.get("result")
                    ):
                        checked_calculations += 1
                        check["calculation_verified"] = True
                    else:
                        check["calculation_verified"] = False
                        issues.append(
                            f"Calculation task {task_id} failed "
                            "independent recalculation."
                        )

        checks.append(check)

    # Verify successful analysis tasks.
    for task in tasks:
        if _task_type(task) != "analysis":
            continue

        task_id = _task_id(task)
        execution = execution_by_id.get(task_id)

        # Failed analysis may already have been classified as safely
        # blocked above.
        if execution is None:
            continue

        output = str(execution.get("output") or "").lower()
        tool_result = execution.get("tool_result") or {}

        # Calculation analysis must be independently reproducible.
        if (
            tool_result.get("verification")
            == "independently_recalculated"
        ):
            if not tool_result.get("success"):
                issues.append(
                    f"Analysis task {task_id} reports an unsuccessful "
                    "verification."
                )
                continue

            expression = tool_result.get("expression")
            recorded_value = tool_result.get("result")

            if expression is None or recorded_value is None:
                issues.append(
                    f"Analysis task {task_id} is missing its "
                    "expression or result."
                )
                continue

            recomputed = calculate(str(expression))

            if not recomputed.get("success"):
                issues.append(
                    f"Analysis task {task_id} could not independently "
                    "recalculate its expression."
                )
                continue

            if not _numbers_match(
                recorded_value, recomputed.get("result")
            ):
                issues.append(
                    f"Analysis task {task_id} has a mismatched "
                    "independently recalculated result."
                )
                continue

            check = next(
                (
                    item for item in checks
                    if item["task_id"] == task_id
                ),
                None,
            )

            if check is not None:
                check["analysis_verified"] = True

            continue

        # Research-backed analysis must identify evidence and limits.
        if not sources:
            issues.append(
                f"Analysis task {task_id} cannot be checked because "
                "no valid research sources were found."
            )
            continue

        if not any(word in output for word in (
            "limitation",
            "missing evidence",
            "not verified",
            "not been performed",
            "unverified",
            "caveat",
        )):
            issues.append(
                f"Analysis task {task_id} does not clearly disclose "
                "evidence limitations."
            )

        if not any(word in output for word in (
            "http://",
            "https://",
            "sources retrieved",
            "source:",
        )):
            issues.append(
                f"Analysis task {task_id} does not identify its "
                "evidence sources."
            )

    passed = not issues

    score = (
        100
        if passed
        else max(
            0,
            round(
                100
                * (
                    len(checks)
                    - sum(
                        not item["execution_success"]
                        and not item["safe_rejection"]
                        and not item["blocked_safely"]
                        or item["research_success"] is False
                        or item.get("calculation_verified") is False
                        for item in checks
                    )
                )
                / max(len(checks), 1)
            )
            - min(20, 5 * len(issues)),
        )
    )

    if passed and safe_rejections:
        summary = (
            "Verification passed: the invalid calculation was safely "
            "rejected, no numerical result was accepted, and dependent "
            "analysis was blocked where applicable. This does not mean "
            "the requested arithmetic produced a valid result."
        )
    elif passed:
        summary = (
            "Structural verification passed: task execution, applicable "
            "research evidence, and calculation consistency were checked. "
            "Research claims have not been independently fact-checked."
        )
    else:
        summary = (
            "Structural verification found issues. Review the listed "
            "issues before treating this workflow as complete."
        )

    result = {
        "passed": passed,
        "score": score,
        "checks": checks,
        "sources": sources,
        "issues": issues,
        "summary": summary,
        "verification_method": "deterministic_structural_checks",
        "checked_calculations": checked_calculations,
        "checked_research_tasks": checked_research,
        "safe_rejections": safe_rejections,
        "safely_blocked_tasks": safely_blocked_tasks,
        "source_count": len(sources),
        "independent_fact_check": False,
    }

    state.verification_results.append(result)
    state.workflow_status = (
        "verification_passed" if passed else "verification_failed"
    )

    state.add_log(
        "Verification Agent finished: "
        f"{'PASSED' if passed else 'FAILED'} "
        f"(score {score}/100; method: deterministic structural checks)."
    )

    return result

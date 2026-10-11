import re

from tools.calculator import calculate
from tools.retrieval import search_wikipedia


def get_task_id(task):
    return task.get("task_id", task.get("id", "unknown"))


def get_task_type(task):
    task_type = str(
        task.get("task_type", task.get("type", "general"))
    ).lower().strip()

    if task_type in {"calculation", "calculator", "math"}:
        return "calculation"

    if task_type in {"analysis", "research"}:
        return task_type

    description = str(task.get("description", "")).lower()

    if any(
        word in description
        for word in (
            "calculate",
            "calculation",
            "total cost",
            "multiply",
            "arithmetic",
            "sum of",
        )
    ):
        return "calculation"

    return task_type or "general"


def extract_expression(description):
    """Extract a complete arithmetic expression from task text."""

    text = str(description or "").lower()
    text = text.replace(",", "")
    text = text.replace("₹", " rs ")
    text = text.replace("×", "*").replace("÷", "/")
    text = text.replace("−", "-")

    # Convert common written operators into symbols.
    replacements = [
        (r"\bdivided\s+by\s+zero\b", "/ 0"),
        (r"\bdivided\s+by\s+(\d+(?:\.\d+)?)\b", r"/ \1"),
        (r"\bmultiplied\s+by\b", "*"),
        (r"\btimes\b", "*"),
        (r"\bplus\b", "+"),
        (r"\bminus\b", "-"),
    ]

    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text)

    # Convert item descriptions into a sum.
    # Example: 5 notebooks at Rs 40 each.
    item_pattern = re.compile(
        r"(\d+(?:\.\d+)?)\s+[\w-]+\s+at\s+"
        r"(?:rs\.?\s*)?(\d+(?:\.\d+)?)\s+each"
    )

    items = item_pattern.findall(text)

    if items:
        return "+".join(
            f"({quantity}*{price})"
            for quantity, price in items
        )

    # Match expressions containing parenthesized terms.
    # Example: (5*40)+(3*10).
    number = r"[-+]?\d+(?:\.\d+)?"
    atom = rf"(?:{number}|\([^()]*\))"
    operator_pattern = r"(?:\*\*|//|[+\-*/%])"

    expression_pattern = re.compile(
        rf"(?<![\w.]){atom}"
        rf"(?:\s*{operator_pattern}\s*{atom})+"
    )

    candidates = expression_pattern.findall(text)

    if not candidates:
        return None

    # Prefer the longest complete arithmetic expression.
    expression = max(candidates, key=len)
    expression = re.sub(r"\s+", "", expression)

    # The calculator validates syntax and supported operators.
    return expression


def _state_results(state):
    results = getattr(state, "execution_results", [])
    return results if isinstance(results, list) else []


def _successful_research(state):
    for item in reversed(_state_results(state)):
        if not item.get("success"):
            continue

        tool_result = item.get("tool_result")

        if (
            str(item.get("task_type", "")).lower() == "research"
            and isinstance(tool_result, dict)
            and tool_result.get("success")
        ):
            return item

    return None


def _format_sources(sources):
    lines = []

    for index, source in enumerate(sources, start=1):
        if not isinstance(source, dict):
            continue

        title = source.get("title") or "Untitled source"
        url = source.get("url") or source.get("link") or "URL unavailable"
        snippet = (
            source.get("snippet")
            or source.get("extract")
            or source.get("summary")
            or ""
        )

        lines.append(f"{index}. {title}\n   URL: {url}")

        if snippet:
            lines.append(f"   Retrieved evidence: {snippet}")

    return "\n".join(lines) if lines else "No usable sources were returned."


def _research_analysis(sources):
    evidence_blocks = []

    for index, source in enumerate(sources, start=1):
        title = str(source.get("title", "Untitled source"))
        url = str(source.get("url") or source.get("link"))
        snippet = str(
            source.get("snippet")
            or source.get("extract")
            or source.get("summary")
            or ""
        ).strip()

        evidence_blocks.append(
            f"{index}. {title}\n"
            f"   URL: {url}\n"
            f"   Retrieved evidence: {snippet or 'No excerpt available.'}"
        )

    return (
        "Evidence-based research analysis\n\n"
        "Retrieved sources:\n"
        + "\n\n".join(evidence_blocks)
        + "\n\nLimitations:\n"
        "- This analysis uses retrieved excerpts only.\n"
        "- The excerpts may omit context from the full articles.\n"
        "- The presence of a source does not independently prove every claim."
    )


def execute_task(state, task):
    task_id = get_task_id(task)
    task_type = get_task_type(task)
    description = str(task.get("description", "")).strip()

    result = {
        "task_id": task_id,
        "task_type": task_type,
        "description": description,
        "success": False,
        "output": "",
        "tool_result": None,
        "fallback_used": True,
        "error": None,
    }

    # RESEARCH
    if task_type == "research":
        query = re.sub(
            r"^(retrieve relevant information and source evidence for:\s*)",
            "",
            description,
            flags=re.IGNORECASE,
        ).strip()

        try:
            tool_result = search_wikipedia(query, 3)
            result["tool_result"] = tool_result

            if not isinstance(tool_result, dict):
                raise ValueError("Unexpected retrieval result.")

            sources = tool_result.get("results", [])

            if not tool_result.get("success") or not sources:
                error = (
                    tool_result.get("error")
                    or "No relevant sources retrieved."
                )
                result["error"] = error
                result["output"] = f"Research failed: {error}"
                return result

            result["success"] = True
            result["output"] = (
                f"Research query: {tool_result.get('query', query)}\n"
                f"Sources retrieved: {len(sources)}\n\n"
                f"{_format_sources(sources)}"
            )
            return result

        except Exception as exc:
            result["error"] = f"Research retrieval failed: {exc}"
            result["output"] = result["error"]
            return result

    # CALCULATION
    if task_type == "calculation":
        expression = extract_expression(description)

        if not expression:
            result["error"] = (
                "Could not identify a supported arithmetic expression."
            )
            result["output"] = result["error"]
            return result

        tool_result = calculate(expression)
        result["tool_result"] = tool_result

        if not tool_result.get("success"):
            result["error"] = tool_result.get(
                "error", "Calculation failed."
            )
            result["output"] = (
                "Calculation could not be completed.\n"
                f"Expression: {expression}\n"
                f"Reason: {result['error']}"
            )
            return result

        value = tool_result["result"]
        result["success"] = True
        result["output"] = (
            f"Expression: {expression}\n"
            f"Calculation: {expression} = {value:g}\n"
            f"Result: {value:g}"
        )
        return result

    # ANALYSIS
    if task_type == "analysis":
        research = _successful_research(state)

        if research:
            sources = research["tool_result"].get("results", [])

            usable_sources = [
                source
                for source in sources
                if isinstance(source, dict)
                and source.get("title")
                and (source.get("url") or source.get("link"))
            ]

            if not usable_sources:
                result["error"] = (
                    "Research returned no usable titled sources with URLs."
                )
                result["output"] = result["error"]
                return result

            result["success"] = True
            result["tool_result"] = {
                "success": True,
                "analysis_type": "research",
                "source_count": len(usable_sources),
                "sources": usable_sources,
                "limitations": (
                    "Analysis uses retrieved excerpts and is not an "
                    "independent factual verification."
                ),
            }
            result["output"] = _research_analysis(usable_sources)
            return result

        # Find the most recent calculation, including failed calculations.
        calculations = [
            item
            for item in _state_results(state)
            if item.get("task_type") == "calculation"
        ]

        if calculations:
            calculation = calculations[-1]
            tool_result = calculation.get("tool_result")

            if not calculation.get("success"):
                error = (
                    tool_result.get("error")
                    if isinstance(tool_result, dict)
                    else calculation.get("error")
                ) or "The required calculation did not succeed."

                result["error"] = (
                    "Analysis blocked because the required calculation "
                    f"failed: {error}"
                )
                result["output"] = (
                    "No verified numerical result can be provided.\n"
                    f"Reason: {error}\n"
                    "The calculation must succeed before this analysis "
                    "can be verified."
                )
                return result

            if not isinstance(tool_result, dict):
                result["error"] = "Calculation result is missing."
                result["output"] = result["error"]
                return result

            expression = tool_result.get("expression")
            recorded_value = tool_result.get("result")

            if expression is None or recorded_value is None:
                result["error"] = (
                    "Recorded calculation is missing its expression or result."
                )
                result["output"] = result["error"]
                return result

            checked = calculate(expression)

            if not checked.get("success"):
                result["error"] = (
                    "Independent recalculation failed: "
                    + str(checked.get("error", "Unknown error"))
                )
                result["output"] = result["error"]
                return result

            try:
                matches = (
                    abs(float(recorded_value) - float(checked["result"]))
                    <= 1e-9
                )
            except (TypeError, ValueError):
                matches = False

            if not matches:
                result["error"] = (
                    "Recorded result does not match the independently "
                    "recalculated result."
                )
                result["output"] = result["error"]
                return result

            result["success"] = True
            result["tool_result"] = {
                "success": True,
                "expression": expression,
                "result": checked["result"],
                "verification": "independently_recalculated",
            }
            result["output"] = (
                f"Expression: {expression}\n"
                f"Recorded result: {recorded_value}\n"
                f"Independently recalculated result: {checked['result']}\n"
                "Verification: PASS - both results match."
            )
            return result

        result["error"] = (
            "Analysis requires successful research or calculation."
        )
        result["output"] = result["error"]
        return result

    result["error"] = f"Unsupported task type: {task_type}"
    result["output"] = result["error"]
    return result

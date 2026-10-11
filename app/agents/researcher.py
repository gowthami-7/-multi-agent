
import re

from tools.retrieval import search_wikipedia


def _clean_query(text: str) -> str:
    """Turn a workflow request into a focused Wikipedia search query."""

    text = str(text or "").strip()

    prefixes = [
        "retrieve relevant information and source evidence for:",
        "research the following:",
        "research:",
    ]

    lower_text = text.lower()
    for prefix in prefixes:
        if lower_text.startswith(prefix):
            text = text[len(prefix):].strip()
            break

    # Remove common instructions that are not part of the topic.
    text = re.sub(
        r"\b(retrieve relevant information|from wikipedia|"
        r"summarize the key findings|include source titles and urls|"
        r"verify that the summary is supported by the retrieved sources|"
        r"verify the result|do not invent facts)\b",
        " ",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(r"\s+", " ", text).strip(" .,:;")
    return text or "general knowledge"


def _build_local_summary(results: list) -> str:
    """
    Build a source-grounded extractive summary from retrieved Wikipedia
    excerpts. This does not use an LLM or add outside factual claims.
    """

    parts = [
        "LOCAL EXTRACTIVE SUMMARY",
        "AI summarization was unavailable, so this summary uses only "
        "the excerpts returned by Wikipedia retrieval.",
        "",
    ]

    usable = []

    for item in results:
        title = str(item.get("title") or "Untitled source").strip()
        snippet = str(item.get("snippet") or "").strip()
        url = str(item.get("url") or "").strip()

        if snippet:
            usable.append({
                "title": title,
                "snippet": snippet,
                "url": url,
            })

    if not usable:
        return ""

    parts.append("Key findings from retrieved excerpts:")

    for item in usable:
        parts.append(f"- {item['title']}: {item['snippet']}")

    parts.extend([
        "",
        "Evidence limitation: these findings reflect retrieved excerpts, "
        "not a complete review of the linked articles.",
    ])

    return "\n".join(parts)


def research_task(state, task: dict) -> dict:
    """
    Research Agent:
    Retrieves Wikipedia excerpts and creates a local extractive summary.
    Does not require an LLM or OpenRouter quota.
    """

    task_id = task.get("task_id")
    description = str(task.get("description") or "").strip()

    # Prefer the original user request because task descriptions may
    # contain workflow instructions rather than just the topic.
    user_request = str(getattr(state, "user_request", "") or "").strip()
    query = _clean_query(user_request or description)

    state.add_log(f"Research Agent started task {task_id}.")

    result = {
        "success": False,
        "task_id": task_id,
        "query": query,
        "findings": "",
        "sources": [],
        "error": None,
        "summarization_method": "local_extractive",
    }

    try:
        retrieval = search_wikipedia(query, max_results=5)

        if not isinstance(retrieval, dict):
            raise RuntimeError(
                "Wikipedia retrieval returned an unexpected response."
            )

        retrieved_items = retrieval.get("results") or []

        # Keep the real retrieved titles, URLs, and excerpts.
        sources = []
        for item in retrieved_items:
            title = str(item.get("title") or "Untitled source").strip()
            url = str(item.get("url") or "").strip()
            snippet = str(item.get("snippet") or "").strip()

            if title or url:
                sources.append({
                    "title": title,
                    "url": url,
                    "snippet": snippet,
                })

        result["sources"] = sources

        findings = _build_local_summary(retrieved_items)

        if not findings:
            retrieval_error = retrieval.get("error")
            result["error"] = (
                str(retrieval_error)
                if retrieval_error
                else "Wikipedia retrieval returned no usable excerpts."
            )
        else:
            result.update({
                "success": True,
                "findings": findings,
                "error": None,
            })

            state.add_log(
                f"Research Agent retrieved {len(sources)} source(s) "
                f"for task {task_id} using local extractive summarization."
            )

    except Exception as exc:
        result["error"] = str(exc)
        state.add_error(f"Research Agent failed: {exc}")
        state.add_log(
            f"Research Agent could not complete task {task_id}."
        )

    state.research_results.append(result)

    if not result["success"]:
        state.add_error(
            f"Research task {task_id} could not be completed: "
            f"{result.get('error') or 'No usable research excerpts.'}"
        )

    return result

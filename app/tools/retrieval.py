
import json
import re
from html import unescape
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
USER_AGENT = "AgentFlowAI/1.0 (educational research project)"

STOP_WORDS = {
    "the", "and", "for", "with", "from", "that", "this", "these",
    "those", "what", "when", "where", "which", "their", "there",
    "about", "into", "your", "have", "has", "had", "are", "was",
    "were", "will", "would", "could", "should", "can", "may",
    "main", "key", "important", "information", "research", "retrieve",
    "search", "summarize", "summary", "include", "source", "sources",
    "title", "titles", "url", "urls", "verify", "verified", "supported",
    "relevant", "provide", "findings", "points", "permanent", "page",
    "pages", "wikipedia", "explain", "explanation", "causes", "cause",
    "identify", "list", "describe", "task", "agent", "record",
    "benefits", "limitations", "limitation", "evidence", "clearly",
    "independently", "following", "retrieved", "whether", "three",
    "then", "also", "using", "based", "complete", "missing",
}

TOPIC_QUERIES = {
    "solar energy": [
        "Solar energy",
        "Solar power",
        "Solar cell",
        "Solar thermal energy",
    ],
    "renewable energy": [
        "Renewable energy",
        "Solar power",
        "Wind power",
    ],
    "air pollution": [
        "Air pollution",
        "Causes of air pollution",
        "Air quality",
    ],
    "water pollution": [
        "Water pollution",
        "Water quality",
        "Wastewater",
    ],
    "climate change": [
        "Climate change",
        "Global warming",
        "Greenhouse gas emissions",
    ],
}


def _clean_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", unescape(value)).strip()


def _extract_topic(query: str) -> str:
    """Extract the research topic from a longer workflow request."""
    text = query.lower().strip()

    known_topics = [
        "solar energy",
        "renewable energy",
        "air pollution",
        "water pollution",
        "climate change",
        "global warming",
    ]

    for topic in known_topics:
        if topic in text:
            return topic

    text = re.sub(
        r"\b(research|retrieve|sources?|record|summarize|summary|"
        r"include|verify|verified|supported|evidence|findings|"
        r"identify|missing|clearly|independently|up to|three|"
        r"titles|urls?|benefits and limitations of|the|then|"
        r"that|their|by|and)\b",
        " ",
        text,
    )
    text = re.sub(r"[^a-z0-9\s-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or query.strip()


def _search_articles(query: str, max_results: int = 5) -> list:
    params = urlencode({
        "action": "query",
        "list": "search",
        "srsearch": query,
        "format": "json",
        "srlimit": max_results,
    })

    request = Request(
        f"{WIKIPEDIA_API}?{params}",
        headers={"User-Agent": USER_AGENT},
    )

    with urlopen(request, timeout=12) as response:
        data = json.loads(response.read().decode("utf-8"))

    return data.get("query", {}).get("search", [])


def _get_extract(page_id: int) -> str:
    params = urlencode({
        "action": "query",
        "pageids": page_id,
        "prop": "extracts",
        "explaintext": 1,
        "exintro": 1,
        "format": "json",
    })

    request = Request(
        f"{WIKIPEDIA_API}?{params}",
        headers={"User-Agent": USER_AGENT},
    )

    with urlopen(request, timeout=12) as response:
        data = json.loads(response.read().decode("utf-8"))

    page = data.get("query", {}).get("pages", {}).get(
        str(page_id), {}
    )
    return page.get("extract", "").strip()


def _expanded_queries(query: str) -> list:
    topic = _extract_topic(query).lower()

    for known_topic, queries in TOPIC_QUERIES.items():
        if known_topic in topic:
            return queries.copy()

    return [topic]


def _relevance_score(title: str, snippet: str, query: str) -> int:
    topic = _extract_topic(query).lower()
    title_text = title.lower()
    content = f"{title} {snippet}".lower()

    query_words = {
        word for word in re.findall(r"[a-z]{3,}", topic)
        if word not in STOP_WORDS
    }

    score = sum(2 for word in query_words if word in content)

    if title_text.strip() == topic:
        score += 12
    elif topic in title_text:
        score += 8

    if any(word in title_text for word in query_words):
        score += 3

    if "solar energy" in topic:
        if "solar" in title_text:
            score += 8
        if "solar" in content and (
            "energy" in content or "electricity" in content
        ):
            score += 4

    return score


def _matches_topic(title: str, snippet: str, original_query: str) -> bool:
    text = f"{title} {snippet}".lower()
    topic = _extract_topic(original_query).lower()

    topic_terms = {
        "solar energy": (
            "solar", "photovoltaic", "solar cell",
            "solar power", "solar thermal",
        ),
        "renewable energy": (
            "renewable energy", "solar", "wind power",
            "hydropower", "geothermal",
        ),
        "air pollution": (
            "air pollution", "air pollutant", "air quality",
            "particulate matter", "vehicle emissions",
            "industrial emissions", "fossil fuel", "combustion",
        ),
        "water pollution": (
            "water pollution", "water contaminant",
            "wastewater", "water quality",
        ),
        "climate change": (
            "climate change", "global warming",
            "greenhouse gas", "carbon dioxide",
        ),
        "global warming": (
            "global warming", "climate change",
            "greenhouse gas", "carbon dioxide",
        ),
    }

    for known_topic, terms in topic_terms.items():
        if known_topic in topic:
            return any(term in text for term in terms)

    words = {
        word for word in re.findall(r"[a-z]{3,}", topic)
        if word not in STOP_WORDS
    }
    return bool(words) and any(word in text for word in words)


def search_wikipedia(query: str, max_results: int = 3) -> dict:
    """
    Retrieve relevant Wikipedia articles with titles, URLs,
    text evidence, and relevance scores.
    """
    query = (query or "").strip()

    if not query:
        return {
            "success": False,
            "query": query,
            "results": [],
            "error": "Search query cannot be empty.",
        }

    max_results = max(1, min(int(max_results), 5))
    search_queries = _expanded_queries(query)
    articles_by_id = {}
    errors = []

    try:
        for search_query in search_queries:
            try:
                articles = _search_articles(
                    search_query,
                    max_results=max_results,
                )
            except (HTTPError, URLError, TimeoutError, ValueError) as exc:
                errors.append(str(exc))
                continue

            for article in articles:
                page_id = article.get("pageid")
                if page_id and page_id not in articles_by_id:
                    articles_by_id[page_id] = article

        candidates = []

        for page_id, article in articles_by_id.items():
            title = article.get("title", "")
            search_snippet = _clean_text(article.get("snippet", ""))

            try:
                extract = _get_extract(page_id)
            except (HTTPError, URLError, TimeoutError, ValueError) as exc:
                errors.append(str(exc))
                extract = ""

            evidence = " ".join(
                part for part in (search_snippet, extract) if part
            ).strip()

            if not evidence:
                continue

            if not _matches_topic(title, evidence, query):
                continue

            candidates.append({
                "title": title,
                "url": (
                    "https://en.wikipedia.org/?curid="
                    + str(page_id)
                ),
                "snippet": evidence[:2500],
                "relevance_score": _relevance_score(
                    title, evidence, query
                ),
            })

        candidates.sort(
            key=lambda item: item["relevance_score"],
            reverse=True,
        )
        results = candidates[:max_results]

        if results:
            error = None
        elif errors:
            error = (
                "Wikipedia retrieval encountered errors: "
                + "; ".join(errors[:2])
            )
        else:
            error = (
                "No sufficiently relevant sources were found. "
                "The search may be unavailable or results did not "
                "meet the topic relevance checks."
            )

        return {
            "success": bool(results),
            "query": _extract_topic(query),
            "results": results,
            "error": error,
        }

    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        return {
            "success": False,
            "query": _extract_topic(query),
            "results": [],
            "error": f"Wikipedia retrieval failed: {exc}",
        }

"""Web search for the tutor, through Tavily.

Used only for things the syllabus cannot answer: board announcements, date
sheets, results, and questions the student asks that sit outside FSc. Syllabus
content comes from the SLOs and the teacher-reviewed bank, never from here.

Needs ``TAVILY_API_KEY``. Without it the tool is not offered to the tutor at
all, so the chat works exactly as before.
"""

import os

import httpx
from langchain.tools import tool

ENDPOINT = "https://api.tavily.com/search"
TIMEOUT = 20.0
MAX_RESULTS = 4
# FBISE's own site, for anything about the board itself
OFFICIAL = ["fbise.edu.pk"]


def api_key() -> str:
    return (os.getenv("TAVILY_API_KEY") or "").strip()


def _format(data: dict) -> str:
    results = data.get("results") or []
    if not results:
        return "The web search found nothing useful. Say so rather than guessing."
    lines = []
    for item in results[:MAX_RESULTS]:
        title = (item.get("title") or "").strip() or "Untitled"
        url = (item.get("url") or "").strip()
        content = " ".join((item.get("content") or "").split())[:700]
        lines.append(f"- {title}\n  {url}\n  {content}")
    return (
        "Web results. Use them only if they answer the question, say the answer came "
        "from the web, and name the source:\n" + "\n".join(lines)
    )


@tool(parse_docstring=True)
async def search_web(query: str, official_only: bool = False) -> str:
    """Search the web for something the FSc syllabus cannot answer.

    Use this for FBISE announcements, date sheets, results and exam news, and for
    questions the student asks that are outside the FSc syllabus. Do NOT use it for
    syllabus topics: those are answered from the SLOs and the reviewed bank. Use it
    at most once per question.

    Args:
        query: What to search for, in English.
        official_only: True to search only FBISE's own website, for anything about
            the board itself (dates, notifications, results, rules).
    """
    key = api_key()
    if not key:
        return "Web search is not available. Answer from the syllabus instead."

    payload: dict = {
        "query": query[:400],
        "max_results": MAX_RESULTS,
        "search_depth": "basic",
        "topic": "general",
    }
    if official_only:
        payload["include_domains"] = OFFICIAL

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(
                ENDPOINT, json=payload, headers={"Authorization": f"Bearer {key}"}
            )
            response.raise_for_status()
            return _format(response.json())
    except httpx.HTTPStatusError as e:
        # A spent quota or a bad key must not look like a wrong answer
        if e.response.status_code in (401, 403):
            return "Web search is not set up correctly. Answer from the syllabus instead."
        if e.response.status_code == 429:
            return "Web search has run out of quota for now. Answer from the syllabus instead."
        return "The web search failed. Answer from the syllabus instead, and say so."
    except Exception:
        return "The web search failed. Answer from the syllabus instead, and say so."


# Offered to the tutor only when a key is configured
tools = [search_web] if api_key() else []

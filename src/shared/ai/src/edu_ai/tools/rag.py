"""RAG search tools for agent."""

import os

from edu_ai.chatbot.context import ChatbotContext
from langchain.tools import tool
from langgraph.prebuilt import ToolRuntime

# How close a match has to be before it counts as an answer. Scores run from 0
# to 1, higher being closer.
#
# Without a floor the search always returns its best match, however poor, and
# the tutor believes it: a student asking "what's this?" about a picture was
# once answered from an unrelated mind map, because that was simply the nearest
# thing in the project. Returning nothing is the honest answer to a question
# the documents do not cover, and the tutor then says so.
#
# Tunable, because the right value depends on the embedding model and on what
# a particular student has uploaded.
MIN_SCORE = float(os.getenv("DOCUMENT_SEARCH_MIN_SCORE", "0.45"))


@tool(
    "search_project_documents",
    description="Search project documents for relevant course content. ALWAYS use this for questions about course concepts, definitions, examples, exercises, or any academic topic. Only skip for greetings or purely personal questions.",
)
async def search_project_documents(
    query: str,
    runtime: ToolRuntime[ChatbotContext],
) -> dict:
    """Search project documents and return relevant content."""
    ctx = runtime.context

    # Perform RAG search using SearchService directly
    search_results = await ctx.search.search_documents(
        query=query, project_id=ctx.project_id, top_k=5
    )

    if not search_results:
        return {"content": "No relevant documents found.", "sources": []}

    # Build sources from SearchResultItem
    sources = [
        {
            "id": result.id,
            "content": result.content or "",
            "title": result.title or f"Document {i}",
            "document_id": result.document_id,
            "score": getattr(result, "score", None) or 1.0,
        }
        for i, result in enumerate(search_results, 1)
    ]

    # Two filters, because they catch different failures. The floor drops a
    # search that found nothing good at all. The relative cut drops the weak
    # tail when something good was found - without it one strong match drags
    # unrelated files along with it, and the tutor cites all of them.
    best = max((source["score"] for source in sources), default=0.0)
    close_enough = [
        source
        for source in sources
        if source["score"] >= MIN_SCORE and source["score"] >= best * 0.75
    ]
    if not close_enough:
        # Logged so the floor can be tuned from real traffic, not guessed
        print(f"document search found nothing above {MIN_SCORE}: best was {best:.3f}")
        return {
            "content": (
                "Nothing in the student's documents answers this. Do not use "
                "the documents for this question - answer from the syllabus and "
                "your own knowledge instead, and never describe a file as if it "
                "were what the student asked about."
            ),
            "sources": [],
            "best_score": round(best, 3),
        }
    sources = close_enough

    # Format content for agent - give clean context without citation markers
    # The agent should use this information naturally, not copy-paste it
    context_blocks = [
        f"From {source['title']}:\n{source['content'][:1500]}" for source in sources
    ]

    formatted_content = "\n\n---\n\n".join(context_blocks)

    return {
        "content": (
            "Search results from the student's own uploaded documents. These "
            "are what a search returned, not an answer and not necessarily "
            "relevant: use only what genuinely bears on what was asked, and "
            "ignore the rest.\n\n"
            f"{formatted_content}\n\n"
            "The student asked their question, not a question about these "
            "files. Do not open your reply by announcing what you have read, "
            "do not summarise a document they did not ask about, and if none "
            "of this bears on the question, answer from the syllabus and your "
            "own knowledge instead."
        ),
        "sources": sources,  # This will be captured by middleware
    }


# Export tools
tools = [search_project_documents]

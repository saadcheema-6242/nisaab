"""Check the configured AI provider: models, chat, tool calling, embeddings.

Reads the same settings as the API and worker (repository root .env plus the
environment), so it can check local Gemini or Vertex AI before a deploy.

Usage (from the repository root):
    uv run --package edu-api python scripts/check_llm.py

For Vertex AI from a laptop, first run `gcloud auth application-default login`, then:
    LLM_PROVIDER=vertex GOOGLE_CLOUD_PROJECT=your-project \
        uv run --package edu-api python scripts/check_llm.py
"""

import sys

from edu_ai.llm import (
    GENERATION,
    MARKING,
    OCR,
    TUTOR,
    create_chat_model,
    create_embeddings,
    get_llm_settings,
    is_llm_configured,
)

EXPECTED_DIMENSIONS = 3072


def get_weather(city: str) -> str:
    """Get the weather for a city."""
    return "sunny"


def main() -> None:
    settings = get_llm_settings()
    print(f"Provider: {settings.provider}  base URL: {settings.base_url}")
    for task in (TUTOR, GENERATION, MARKING, OCR):
        print(f"  {task:<10} -> {settings.model_for(task)}")
    print(f"  fallbacks  -> {settings.fallback_models or 'none'}")
    print(f"  embeddings -> {settings.embedding_model}")

    if not is_llm_configured():
        sys.exit("Not configured: set LLM_API_KEY (gemini/openai) or GOOGLE_CLOUD_PROJECT (vertex)")

    failures = []
    for task in (TUTOR, GENERATION):
        try:
            reply = create_chat_model(task=task).invoke("Reply with exactly: OK").content
            print(f"[PASS] {task} chat: {reply!r}")
        except Exception as e:
            failures.append(task)
            print(f"[FAIL] {task} chat: {e}")

    try:
        msg = create_chat_model(task=TUTOR).bind_tools([get_weather]).invoke(
            "What's the weather in Islamabad? Use the tool."
        )
        ok = bool(msg.tool_calls)
        print(f"[{'PASS' if ok else 'FAIL'}] tool calling: {msg.tool_calls}")
        if not ok:
            failures.append("tools")
    except Exception as e:
        failures.append("tools")
        print(f"[FAIL] tool calling: {e}")

    try:
        dims = len(create_embeddings().embed_query("Newton's second law of motion"))
        ok = dims == EXPECTED_DIMENSIONS
        print(f"[{'PASS' if ok else 'FAIL'}] embeddings: {dims} dimensions (database expects {EXPECTED_DIMENSIONS})")
        if not ok:
            failures.append("embeddings")
    except Exception as e:
        failures.append("embeddings")
        print(f"[FAIL] embeddings: {e}")

    if failures:
        sys.exit(f"FAILED: {', '.join(failures)}")
    print("All checks passed")


if __name__ == "__main__":
    main()

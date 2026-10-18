"""Check the web search tool's formatting and failure handling without the
project venv: stub langchain's @tool so the function stays a plain coroutine."""

import asyncio
import sys
import types
from pathlib import Path

# --- stub langchain.tools.tool as a pass-through
lc = types.ModuleType("langchain")
lc_tools = types.ModuleType("langchain.tools")
def _tool(*a, **kw):
    if a and callable(a[0]):
        return a[0]
    return lambda fn: fn
lc_tools.tool = _tool
lc.tools = lc_tools
sys.modules.setdefault("langchain", lc)
sys.modules["langchain.tools"] = lc_tools

import os
os.environ["TAVILY_API_KEY"] = "test-key-not-real"
sys.path.insert(0, str(Path(r"D:\final-nissab\edu-agent\src\shared\ai\src")))
import httpx
from edu_ai.tools import web

ok = []
def check(name, cond, detail=""):
    ok.append(cond)
    print(("  PASS " if cond else "  FAIL ") + name + (f" :: {detail}" if detail else ""))

print("1. formatting")
out = web._format({"results": [
    {"title": "FBISE Date Sheet HSSC-I 2026", "url": "https://fbise.edu.pk/ds.pdf",
     "content": "The   annual\nexamination  begins on 5 May 2026."},
    {"title": "", "url": "https://x.test/a", "content": "x" * 900},
]})
check("includes the title and url", "FBISE Date Sheet" in out and "fbise.edu.pk/ds.pdf" in out)
check("collapses whitespace", "annual examination begins" in out, out[:120])
check("untitled fallback", "Untitled" in out)
check("truncates long content", max(len(l) for l in out.split("\n")) < 760)
check("tells the model to cite", "name the source" in out)

empty = web._format({"results": []})
check("empty result is honest", "found nothing" in empty, empty)

print("2. no key configured")
os.environ["TAVILY_API_KEY"] = ""
r = asyncio.run(web.search_web("anything"))
check("falls back to the syllabus", "not available" in r, r)
os.environ["TAVILY_API_KEY"] = "test-key-not-real"

print("3. failures never look like answers")
cases = {401: "not set up correctly", 403: "not set up correctly",
         429: "run out of quota", 500: "failed"}
for code, expect in cases.items():
    def handler(request, code=code):
        return httpx.Response(code, json={})
    orig = httpx.AsyncClient
    class FakeClient(orig):
        def __init__(self, **kw):
            super().__init__(transport=httpx.MockTransport(handler), **kw)
    httpx.AsyncClient = FakeClient
    try:
        r = asyncio.run(web.search_web("x"))
    finally:
        httpx.AsyncClient = orig
    check(f"HTTP {code}", expect in r, r)

def boom(request):
    raise httpx.ConnectError("no network")
orig = httpx.AsyncClient
class FakeClient(orig):
    def __init__(self, **kw):
        super().__init__(transport=httpx.MockTransport(boom), **kw)
httpx.AsyncClient = FakeClient
try:
    r = asyncio.run(web.search_web("x"))
finally:
    httpx.AsyncClient = orig
check("network error", "failed" in r, r)

print("4. the request we actually send")
sent = {}
def capture(request):
    import json
    sent["url"] = str(request.url)
    sent["auth"] = request.headers.get("authorization", "")
    sent["body"] = json.loads(request.content)
    return httpx.Response(200, json={"results": [
        {"title": "T", "url": "https://fbise.edu.pk/x", "content": "c"}]})
orig = httpx.AsyncClient
class FakeClient(orig):
    def __init__(self, **kw):
        super().__init__(transport=httpx.MockTransport(capture), **kw)
httpx.AsyncClient = FakeClient
try:
    asyncio.run(web.search_web("fbise date sheet", official_only=True))
finally:
    httpx.AsyncClient = orig
check("hits Tavily", sent["url"] == "https://api.tavily.com/search", sent["url"])
check("sends the key as a bearer token", sent["auth"].startswith("Bearer "))
check("official_only restricts to FBISE", sent["body"].get("include_domains") == ["fbise.edu.pk"], str(sent["body"].get("include_domains")))
check("basic depth (1 credit, not 2)", sent["body"]["search_depth"] == "basic")
check("asks for few results", sent["body"]["max_results"] == 4)

sent.clear()
httpx.AsyncClient = FakeClient
try:
    asyncio.run(web.search_web("photosynthesis news"))
finally:
    httpx.AsyncClient = orig
check("open search has no domain filter", "include_domains" not in sent["body"])
check("query is capped", len(sent["body"]["query"]) <= 400)

print()
print(f"{sum(ok)}/{len(ok)} passed")
sys.exit(0 if all(ok) else 1)

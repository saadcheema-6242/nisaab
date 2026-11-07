"""Prove the API reference is hidden when it is meant to be.

Run with:
    python scripts/admin/check_docs_gate.py

Hiding the Scalar page while leaving /openapi.json up would hide nothing:
the JSON is the whole API surface and the page is only a reader for it. So
both are checked.

Importing the real app here is not possible on a laptop - it pulls in
edu_db, edu_ai, openai, langchain and the Google client libraries - so this
splits in two. The part that could genuinely surprise us (does removing the
route also break generating the spec, which client generation depends on?)
is proved against a real FastAPI app with no project imports at all. The
wiring is then read out of the source. Neither needs a database, a network
or a key.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
API_DIR = ROOT / "src" / "edu-api"

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}" + (f"  -- {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(name)


print("what openapi_url=None actually does, against a real FastAPI app")
try:
    from fastapi import FastAPI

    shut = FastAPI(title="probe", docs_url=None, redoc_url=None, openapi_url=None)

    @shut.get("/api/v1/thing")
    async def _thing() -> dict:
        return {}

    served = {getattr(r, "path", None) for r in shut.routes}
    check("no /openapi.json route is served", "/openapi.json" not in served)
    check("no /docs", "/docs" not in served)
    check("no /redoc", "/redoc" not in served)
    check("the real routes are untouched", "/api/v1/thing" in served)

    # The one that matters: pnpm run gen:client calls app.openapi() in process
    # (scripts/export_openapi.py). If removing the route also removed the
    # ability to generate the spec, hiding the docs would break the web client
    # build, and it would break at generation time rather than here.
    spec = shut.openapi()
    check("app.openapi() still generates the spec", bool(spec.get("paths")))
    check("and the route is in it", "/api/v1/thing" in spec.get("paths", {}))

    open_app = FastAPI(title="probe", openapi_url="/openapi.json")
    served_open = {getattr(r, "path", None) for r in open_app.routes}
    check("with it set, the route is served", "/openapi.json" in served_open)
except ImportError:
    check("fastapi is importable", False, "pip install fastapi to run this part")

print()
print("how the API is wired")
main_src = (API_DIR / "main.py").read_text(encoding="utf-8")
check("the docs are read from settings, not hardcoded",
      "get_settings().api_docs" in main_src)
check("openapi_url is conditional on it",
      'openapi_url="/openapi.json" if docs_on else None' in main_src)
check("Swagger stays off", "docs_url=None" in main_src)
check("ReDoc stays off", "redoc_url=None" in main_src)
check("the Scalar page is not mounted when the docs are off",
      "if not get_settings().api_docs:\n            return" in main_src)

cfg_src = (API_DIR / "config.py").read_text(encoding="utf-8")
check("off is the default, so a deployment that says nothing stays shut",
      "api_docs: bool = False" in cfg_src)

print()
print("a rejected token says it was rejected and nothing else")
auth_src = (API_DIR / "auth.py").read_text(encoding="utf-8")
check("the library's own wording is not returned",
      'detail=f"Invalid token: {e!s}"' not in auth_src)
check("nor is the generic failure",
      'detail=f"Authentication failed: {e!s}"' not in auth_src)
check("the caller is told it was invalid", 'detail="Invalid token"' in auth_src)
check("the reason is logged instead", "logger.warning(" in auth_src)
check("the unexpected case keeps its traceback", "logger.exception(" in auth_src)
check("expiry is still told apart, because that one is actionable",
      '"Token has expired"' in auth_src)
check("a missing token is still its own case",
      "Authentication credentials missing" in auth_src)

print()
print("the deploy carries the setting through")
deploy_src = (ROOT / "deploy/gcp/deploy.sh").read_text(encoding="utf-8")
check("API_DOCS is in the environment the services get",
      "API_DOCS" in deploy_src,
      "add it to common_env() or the service never sees it")

print()
if failures:
    print(f"{len(failures)} failed: " + ", ".join(failures))
    sys.exit(1)
print("all checks passed")

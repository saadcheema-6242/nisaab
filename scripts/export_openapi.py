"""Write the API's OpenAPI spec to a file without starting the server.

Usage (from the repository root):
    uv run --package edu-api python scripts/export_openapi.py src/edu-web/openapi.json
"""

import json
import os
import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1] / "src" / "edu-api"


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "openapi.json").resolve()
    sys.path.insert(0, str(API_DIR))
    os.chdir(API_DIR)
    from main import Api, ApiConfig

    spec = Api(ApiConfig(name="Edu API", port=0)).app.openapi()
    out.write_text(json.dumps(spec, indent=2), encoding="utf-8")
    print(f"OpenAPI spec -> {out}")


if __name__ == "__main__":
    main()

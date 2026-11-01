"""Search Wikimedia Commons for real FSc diagrams and show what comes back.

Run with:
    python scripts/admin/try_media_search.py
    python scripts/admin/try_media_search.py "benzene structural formula"

The offline rules are checked by check_openly_licensed.py. This is the other
half: whether Commons actually holds usable diagrams for the things FSc
students study, and whether the licence of each one reads sensibly. Worth
running before trusting the tool with a student's question - a search that
returns nothing usable should return nothing, not something wrong.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/shared/core/src"))

from edu_core.openly_licensed import SearchError, search  # noqa: E402

# The kinds of picture matplotlib cannot draw, which is the point of searching
QUERIES = [
    "projectile motion diagram",
    "benzene structural formula",
    "animal cell diagram labelled",
    "human eye anatomy diagram",
    "free body diagram inclined plane",
    "DNA double helix diagram",
    "electromagnetic spectrum diagram",
    "photosynthesis diagram",
    "Wheatstone bridge circuit",
    "mitosis stages diagram",
]


def main() -> int:
    queries = sys.argv[1:] or QUERIES
    missing = 0

    for query in queries:
        print(f"\n{query}")
        try:
            results = search(query, limit=3)
        except SearchError as error:
            print(f"  search failed: {error}")
            missing += 1
            continue

        if not results:
            print("  nothing usable (either no match, or none freely licensed)")
            missing += 1
            continue

        for found in results:
            print(f"  {found.title[:68]}")
            print(f"    {found.credit.line()[:100]}")
            print(f"    {found.width}x{found.height} {found.mime}")
            print(f"    {found.image_url[:100]}")

    print()
    print(f"{len(queries) - missing} of {len(queries)} queries found a usable picture")
    if missing:
        print("Where nothing was found the tutor must say so, not invent a picture.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

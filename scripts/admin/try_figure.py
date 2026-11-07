"""Draw real figures through Gemini's code execution and keep them to look at.

Run with:
    bash deploy/gcp/deploy.sh script scripts/admin/try_figure.py
    bash deploy/gcp/deploy.sh script scripts/admin/try_figure.py 1

The offline half - the rules the model is given, and the reading of what comes
back - is checked by check_code_run.py, which needs no network. This is the
other half, and it cannot be faked: whether Vertex actually honours the
codeExecution tool, whether matplotlib figures really return as inlined PNG
bytes, and whether what comes out is a figure an FSc student could use.

Each one is saved to the bucket so it can be opened and judged, and the code
the model wrote is printed - that is where a bad figure is diagnosed, not in
the picture.

Pass a number to draw only that one.
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for package in ("core", "ai"):
    sys.path.insert(0, str(ROOT / f"src/shared/{package}/src"))

from edu_core.code_run import figure_prompt  # noqa: E402
from edu_core.storage import create_storage  # noqa: E402
from edu_ai.llm import run_code, supports_code_execution  # noqa: E402

# The first is the question that started this: a student asked for a graph of
# their own vector problem and was given ASCII art, because nothing in the app
# could draw a figure that did not already exist in Wikimedia Commons.
FIGURES = [
    (
        "Physics",
        "head-to-tail addition of three displacement vectors from a common "
        "origin, with the resultant drawn from the start to the final point, "
        "its magnitude and its angle marked",
        "A = 5.0 km due East; B = 8.0 km at 60 degrees North of West; "
        "C = 4.0 km at 30 degrees South of West",
    ),
    (
        "Physics",
        "velocity-time graph for a body starting at rest, accelerating "
        "uniformly, then moving at constant velocity, then decelerating to "
        "rest; shade the area under the graph and mark the total displacement",
        "a = 2.0 m s^-2 for 5.0 s, constant for 10.0 s, then decelerates to "
        "rest in 4.0 s",
    ),
    (
        "Physics",
        "free-body diagram of a block on a rough inclined plane, with weight, "
        "normal reaction, friction and the components of weight along and "
        "perpendicular to the slope",
        "mass 5.0 kg, slope 30 degrees, g = 9.8 m s^-2",
    ),
    (
        "Mathematics",
        "graph of a quadratic function with its vertex, axis of symmetry and "
        "both roots marked",
        "y = x^2 - 4x + 3",
    ),
    (
        "Chemistry",
        "graph of volume against pressure for a fixed mass of gas at constant "
        "temperature, showing the inverse relationship, with a second plot of "
        "volume against the reciprocal of pressure beside it",
        "P = 1.0, 2.0, 3.0, 4.0, 5.0 atm; V = 24.0, 12.0, 8.0, 6.0, 4.8 dm^3",
    ),
    (
        "Physics",
        "ray diagram for a converging lens with the object outside twice the "
        "focal length, showing the three standard construction rays and the "
        "image formed",
        "focal length 10 cm, object 30 cm from the lens, object height 4 cm",
    ),
]


def main() -> int:
    if not supports_code_execution():
        print("Code execution needs LLM_PROVIDER=gemini or vertex. Nothing run.")
        return 1

    wanted = FIGURES
    if len(sys.argv) > 1:
        try:
            wanted = [FIGURES[int(sys.argv[1]) - 1]]
        except (ValueError, IndexError):
            print(f"Pick a figure from 1 to {len(FIGURES)}")
            return 1

    # create_storage picks GCS or Supabase from STORAGE_BACKEND, the same way
    # the API does. Constructing StorageService directly meant Supabase every
    # time, and with no arguments at all, so this probe died before it reached
    # the thing it exists to test.
    storage = create_storage(
        backend=os.getenv("STORAGE_BACKEND", "gcs"),
        bucket=os.getenv("STORAGE_BUCKET", ""),
        supabase_url=os.getenv("SUPABASE_URL", ""),
        supabase_service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
    )
    drawn = 0

    for index, (subject, description, given) in enumerate(wanted, 1):
        print()
        print("=" * 72)
        print(f"{index}. {subject}: {description[:60]}...")
        try:
            run = run_code(figure_prompt(description, subject=subject, given=given))
        except Exception as error:  # noqa: BLE001 - a probe reports, it does not raise
            print(f"   FAILED: {type(error).__name__}: {error}")
            continue

        print(f"   outcome: {run.outcome or 'no code ran'}")
        if run.output.strip():
            print(f"   printed: {run.output.strip()[:300]}")
        if run.code:
            print("   --- the code it wrote ---")
            for line in run.code.splitlines():
                print(f"   | {line}")
        else:
            print("   it wrote no code at all - it answered in words")
        if run.text.strip():
            print(f"   said: {run.text.strip()[:300]}")

        if not run.drew_something:
            print("   NO PICTURE")
            continue

        drawn += 1
        for number, picture in enumerate(run.pictures, 1):
            suffix = f"-{number}" if len(run.pictures) > 1 else ""
            path = f"_probe/figure-{index}{suffix}.png"
            storage.upload(path, picture, content_type="image/png")
            print(f"   drew {len(picture):,} bytes -> {path}")
            print(f"   open: {storage.signed_url(path, expires_in=24 * 60 * 60)}")

    print()
    print("=" * 72)
    print(f"{drawn} of {len(wanted)} drew a figure.")
    print("Open each one. A figure that is wrong is worse than none at all,")
    print("so judge the labels and the angles, not whether a picture appeared.")
    return 0 if drawn == len(wanted) else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Try one prompt against the image model and keep the picture.

Run with:
    bash deploy/gcp/deploy.sh script scripts/admin/try_prompt.py

It sends the prompt exactly as written, without the house style that normally
forbids text, and saves the result to the bucket so it can be looked at. The
point is to find out what the model can really do with labels rather than
assume - edu_core.study_images bans them because an image model usually cannot
spell, and that claim is worth testing rather than repeating.

Both versions are made: the prompt as written, and the same prompt with the
no-text style applied, so the two can be compared side by side.
"""

import os
import sys

PROMPT = (
    "A clean, professional educational physics diagram illustrating projectile "
    "motion, isolated on a solid white background. The diagram features a clear "
    "parabolic trajectory line shown as a bright blue dashed vector curve. An "
    "object (a simple red sphere) is captured at multiple intervals along the "
    "arc: launching, ascending, reaching the apex, descending, and hitting the "
    "ground. Vivid, sharp vector arrows indicate the velocity components at each "
    "interval: vertical velocity arrows (Vy) pointing upward during ascent, "
    "shrinking to zero at the peak, and pointing downward during descent, while "
    "horizontal velocity arrows (Vx) remain a constant length pointing strictly "
    "forward throughout the path. Label placeholders like 'Initial Velocity "
    "(v₀)', 'Launch Angle (θ)', 'Maximum Height (H)', and 'Range (R)' "
    "are cleanly laid out with minimal, crisp modern sans-serif typography. "
    "High-resolution, geometric precision, 2D minimalist vector infographic "
    "style, no clutter, no realistic textures."
)

RUNS = [
    ("as written, labels asked for", False, "samples/prompt-labelled.png"),
    ("with the house no-text style", True, "samples/prompt-no-text.png"),
]


def main() -> int:
    from edu_core.image_gen import ImageGenerationError, generate
    from edu_core.storage import create_storage

    bucket = os.getenv("STORAGE_BUCKET", "")
    print(f"model    : {os.getenv('IMAGE_MODEL') or '(default)'}")
    print(f"location : {os.getenv('IMAGE_LOCATION') or '(default)'}")
    print(f"bucket   : {bucket or '(unset - nothing will be kept)'}")
    print()

    storage = (
        create_storage(backend=os.getenv("STORAGE_BACKEND", "gcs"), bucket=bucket)
        if bucket
        else None
    )

    failures = 0
    for label, style, path in RUNS:
        try:
            png = generate(PROMPT, style=style)
        except ImageGenerationError as error:
            print(f"  FAILED  {label}: {error}")
            failures += 1
            continue

        print(f"  made    {label}: {len(png) / 1024:.0f} KB")
        if storage:
            try:
                storage.upload(path, png, content_type="image/png")
                print(f"          kept at gs://{bucket}/{path}")
            except Exception as error:  # noqa: BLE001 - the picture was still made
                print(f"          could not keep it: {error}")

    print()
    print("Look at both before deciding whether the ban on text should stay.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

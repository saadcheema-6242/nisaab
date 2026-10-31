"""Find an image model this project can actually use.

Run with:
    bash deploy/gcp/deploy.sh script scripts/admin/try_image.py

Tries the configured model first, then the other Imagen ids in turn, and
reports which one answers. Google retires these ids and the replacement is not
guessable, so this asks Vertex rather than trusting documentation.

Set the winner as IMAGE_MODEL in deploy/gcp/deploy.env and deploy again. No
code changes: the model id is a setting.
"""

import os
import sys

CANDIDATES = [
    "imagen-4.0-generate-001",
    "imagen-4.0-fast-generate-001",
    "imagen-4.0-generate-preview-06-06",
    "imagen-3.0-generate-002",
    "imagen-3.0-generate-001",
    "imagen-3.0-fast-generate-001",
    "imagegeneration@006",
    "imagegeneration@005",
]

PROMPT = "a wooden block resting on a wooden ramp, side view"


def main() -> int:
    from edu_core.image_gen import DEFAULT_LOCATION, ImageGenerationError, generate

    location = os.getenv("IMAGE_LOCATION") or DEFAULT_LOCATION
    configured = os.getenv("IMAGE_MODEL")
    print(f"project  : {os.getenv('GOOGLE_CLOUD_PROJECT') or '(unset)'}")
    print(f"location : {location}")
    print(f"configured model: {configured or '(none)'}")
    print()

    order = ([configured] if configured else []) + [
        m for m in CANDIDATES if m != configured
    ]

    winners = []
    for model in order:
        os.environ["IMAGE_MODEL"] = model
        try:
            png = generate(PROMPT)
        except ImageGenerationError as error:
            reason = str(error)
            short = "not found" if "404" in reason else reason[:110]
            print(f"  no   {model:38s} {short}")
            continue
        print(f"  YES  {model:38s} {len(png) / 1024:.0f} KB returned")
        winners.append(model)
        break

    print()
    if winners:
        print(f"Set IMAGE_MODEL={winners[0]} in deploy/gcp/deploy.env, then deploy.")
        return 0

    print("No Imagen model answered in this location.")
    print("Next things to check, in order:")
    print("  - try another IMAGE_LOCATION, e.g. us-east4 or europe-west4")
    print("  - confirm Vertex image generation is enabled for the project")
    print("  - the newer Gemini image models use generateContent, not :predict,")
    print("    so they need a different call than edu_core.image_gen makes")
    return 1


if __name__ == "__main__":
    sys.exit(main())

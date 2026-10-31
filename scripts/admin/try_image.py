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

# Gemini image models first: Google has retired the Imagen 4 endpoints, and the
# Gemini family is what replaced them. The Imagen ids stay in the list because
# an older project may still reach one.
CANDIDATES = [
    "gemini-3.1-flash-image",
    "gemini-3-pro-image",
    "gemini-3.1-flash-lite-image",
    "gemini-2.5-flash-image",
    "gemini-2.0-flash-preview-image-generation",
    "imagen-4.0-generate-001",
    "imagen-3.0-generate-002",
    "imagegeneration@006",
]

# An image model may not be served from the location the text models use
LOCATIONS = ["us-central1", "global", "us-east4"]

PROMPT = "a wooden block resting on a wooden ramp, side view"


def main() -> int:
    from edu_core.image_gen import (
        DEFAULT_LOCATION,
        ImageGenerationError,
        generate,
        uses_predict,
    )

    location = os.getenv("IMAGE_LOCATION") or DEFAULT_LOCATION
    configured = os.getenv("IMAGE_MODEL")
    print(f"project  : {os.getenv('GOOGLE_CLOUD_PROJECT') or '(unset)'}")
    print(f"location : {location}")
    print(f"configured model: {configured or '(none)'}")
    print()

    order = ([configured] if configured else []) + [
        m for m in CANDIDATES if m != configured
    ]
    places = [location] + [p for p in LOCATIONS if p != location]

    winners = []
    for place in places:
        os.environ["IMAGE_LOCATION"] = place
        print(f"in {place}:")
        for model in order:
            os.environ["IMAGE_MODEL"] = model
            call = "predict" if uses_predict(model) else "generateContent"
            try:
                png = generate(PROMPT)
            except ImageGenerationError as error:
                reason = str(error)
                short = "not found" if "404" in reason else reason[:90]
                print(f"  no   {model:42s} {call:15s} {short}")
                continue
            print(f"  YES  {model:42s} {call:15s} {len(png) / 1024:.0f} KB")
            winners.append((model, place))
            break
        if winners:
            break
        print()

    print()
    if winners:
        model, place = winners[0]
        print("Put these in deploy/gcp/deploy.env and deploy:")
        print(f"  IMAGE_MODEL={model}")
        print(f"  IMAGE_LOCATION={place}")
        return 0

    print("No image model answered in any of these locations.")
    print("Next things to check:")
    print("  - whether image generation is enabled for this project at all")
    print("  - whether the ids have moved again; Model Garden lists what is live")
    return 1


if __name__ == "__main__":
    sys.exit(main())

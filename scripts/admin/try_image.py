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


SAMPLE_PATH = "samples/image-probe.png"


def _keep(png: bytes) -> None:
    """Put the picture in the bucket so a person can look at it.

    A size in a log says the call worked; it says nothing about whether the
    picture is any good, which for an image model is the only question that
    matters.
    """
    import os

    from edu_core.storage import create_storage

    bucket = os.getenv("STORAGE_BUCKET", "")
    if not bucket:
        print("  (STORAGE_BUCKET is not set, so the sample was not kept)")
        return
    try:
        storage = create_storage(
            backend=os.getenv("STORAGE_BACKEND", "gcs"), bucket=bucket
        )
        storage.upload(SAMPLE_PATH, png, content_type="image/png")
        print(f"  sample kept at gs://{bucket}/{SAMPLE_PATH}")
    except Exception as error:  # noqa: BLE001 - the probe's answer still stands
        print(f"  (could not keep the sample: {error})")


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
            _keep(png)
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

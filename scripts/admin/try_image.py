"""Check whether Imagen will make a picture for this project.

Run with:
    bash deploy/gcp/deploy.sh script scripts/admin/try_image.py

Prints the settings in use and either the size of the PNG it got back or the
exact refusal from Vertex. The chat tool hides that refusal behind a message
meant for the model, so this is the way to see it plainly.
"""

import os
import sys

from edu_core.image_gen import DEFAULT_LOCATION, DEFAULT_MODEL, ImageGenerationError, generate


def main() -> int:
    print("settings")
    print(f"  project  : {os.getenv('GOOGLE_CLOUD_PROJECT') or '(unset)'}")
    print(f"  model    : {os.getenv('IMAGE_MODEL') or DEFAULT_MODEL + '  (default)'}")
    print(f"  location : {os.getenv('IMAGE_LOCATION') or DEFAULT_LOCATION + '  (default)'}")
    print()

    try:
        png = generate("a wooden block resting on a wooden ramp, side view")
    except ImageGenerationError as error:
        print("FAILED\n")
        print(f"  {error}\n")
        print("Read this as:")
        print("  404 / not found        -> the model id has moved; set IMAGE_MODEL")
        print("  403 / permission       -> the service account cannot call Vertex here")
        print("  400 / invalid argument -> the request shape is wrong for this model")
        print("  no image returned      -> the prompt was filtered")
        return 1

    print(f"WORKED - {len(png) / 1024:.0f} KB of PNG returned")
    print("Imagen is reachable and the model id is right.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Check that NISAAB can publish a Google Form, end to end, on Cloud Run.

Run with:
    bash deploy/gcp/deploy.sh script scripts/admin/try_google_form.py

It makes one real, throwaway quiz form and prints the link. Nothing in the app
is touched. Run it after scripts/admin/authorise_google_forms.py and a deploy,
to confirm the stored authorisation works from inside Cloud Run before anyone
demonstrates the feature.

History: this script first tested whether the *service account* could own a
form. It cannot - no Drive storage quota, so Google answers 500 INTERNAL - which
is why the credentials are now one real Google account's refresh token.
"""

import os
import sys
import traceback

from edu_core.services.google_forms import FormsNotConfiguredError, GoogleFormsService

SAMPLE = [
    {
        "question_text": "A body moves in a circle of radius r at constant speed v. "
        "The magnitude of its acceleration is",
        "option_a": "zero",
        "option_b": "v / r",
        "option_c": "v² / r",
        "option_d": "v² r",
        "correct_option": "c",
        "explanation": "Speed is constant but direction is not, so the body accelerates. "
        "That centripetal acceleration is v² / r, directed toward the centre.",
    },
    {
        "question_text": "Which element has the highest first ionisation energy?",
        "option_a": "Na",
        "option_b": "Mg",
        "option_c": "Al",
        "option_d": "Si",
        "correct_option": "d",
        "explanation": "Ionisation energy rises across a period as nuclear charge grows, "
        "so silicon is highest here.",
    },
]


def main() -> int:
    present = [
        name
        for name in (
            "GOOGLE_OAUTH_CLIENT_ID",
            "GOOGLE_OAUTH_CLIENT_SECRET",
            "GOOGLE_OAUTH_REFRESH_TOKEN",
        )
        if os.environ.get(name)
    ]
    print(f"Credentials present: {len(present)} of 3 -> {', '.join(present) or 'none'}")
    print("Publishing a test form...\n")

    try:
        form = GoogleFormsService(
            client_id=os.environ.get("GOOGLE_OAUTH_CLIENT_ID", ""),
            client_secret=os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", ""),
            refresh_token=os.environ.get("GOOGLE_OAUTH_REFRESH_TOKEN", ""),
        ).publish_quiz(
            title="NISAAB test quiz (safe to delete)",
            questions=SAMPLE,
            description="Created to check that form publishing works from Cloud Run.",
        )
    except FormsNotConfiguredError as error:
        print(f"NOT CONFIGURED\n\n  {error}\n")
        print("Fix: run scripts/admin/authorise_google_forms.py on your own machine,")
        print("then deploy again so Cloud Run picks the secrets up.")
        return 1
    except Exception as error:  # noqa: BLE001 - the whole point is to report why
        print("FAILED\n")
        print(f"  {type(error).__name__}: {error}\n")
        body = getattr(getattr(error, "response", None), "text", None)
        if body:
            print(f"  Google said: {body[:900]}\n")
        print("Read this as:")
        print("  403 'has not been used' or 'disabled' -> enable the forms/drive APIs")
        print("  403 permission or scope message       -> the consent screen is missing a scope")
        print("  401 / invalid_grant                   -> re-run the authorise script")
        print("  500 INTERNAL                          -> these are service-account")
        print("     credentials again; a service account cannot own a form.")
        traceback.print_exc()
        return 1

    print("WORKED\n")
    print(f"  form id   : {form.form_id}")
    print(f"  share this: {form.responder_url}")
    print(f"  edit here : {form.edit_url}\n")
    print("Open the share link in a private window: you should be able to answer it")
    print("without signing in, and see your score the moment you submit.")
    print("\nDelete it afterwards from the edit link.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

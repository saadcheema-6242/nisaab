"""Publish a quiz as a Google Form the student can send to friends.

The form is a real Google Form quiz: answer key and explanations attached, and
shared with anyone who has the link. Grades show on the form itself, because a
quiz that does not collect email addresses releases the score the moment the
respondent presses submit. They see what they scored, which questions they lost
and why - none of which has to come back here.

Why a user account and not the service account
----------------------------------------------
A service account *cannot* own a Google Form. Service accounts get no Drive
storage quota and a Form is a Drive file, so a create call answers
``500 INTERNAL`` rather than a 403, which is what makes it look like a fault on
Google's side. Verified against this project on 27 Oct 2026.

The documented ways around it - a shared drive, or domain-wide delegation - both
need Google Workspace. So instead one real Google account authorises this app
once, offline, and its refresh token is kept in Secret Manager. Every form is
created in that account's Drive. Students never sign in to anything.

Run ``scripts/admin/authorise_google_forms.py`` to do that authorisation; it
writes the three secrets itself and never prints the token.

Needs the Google Forms API and the Drive API enabled on the project.
"""

from dataclasses import dataclass

import httpx

from edu_core.plain_math import latex_to_text

FORMS_API = "https://forms.googleapis.com/v1/forms"
DRIVE_API = "https://www.googleapis.com/drive/v3/files"
TOKEN_URI = "https://oauth2.googleapis.com/token"
SCOPES = [
    "https://www.googleapis.com/auth/forms.body",
    "https://www.googleapis.com/auth/drive.file",
]
OPTIONS = ("a", "b", "c", "d")
TIMEOUT = 30.0


class FormsNotConfiguredError(RuntimeError):
    """No Google account has authorised this app yet, so no form can be made."""


@dataclass(frozen=True)
class PublishedForm:
    """Where the form lives once it has been made."""

    form_id: str
    responder_url: str
    edit_url: str


def _options(question: dict, choices: list[str]) -> list[dict]:
    """The four choices, each with its own picture when it has one.

    Google shows an option's image beside its text, which is what makes
    "which of these is benzene?" answerable on the form itself.
    """
    links = question.get("option_image_urls") or {}
    options: list[dict] = []
    for letter, choice in zip(OPTIONS, choices):
        if not choice:
            continue
        option: dict = {"value": choice}
        url = (links.get(letter) or "").strip() if isinstance(links, dict) else ""
        if url:
            option["image"] = {"sourceUri": url, "altText": choice[:1900] or "Option"}
        options.append(option)
    return options


def _question_item(question: dict, index: int) -> dict:
    """One multiple-choice question, with its answer key and its explanation.

    Everything is converted out of LaTeX first. Google Forms shows plain text,
    so an unconverted option arrives on screen as ``$\\sqrt{x^2 + y^2}$``. The
    answer key is picked from the converted choices, so it still matches one of
    them exactly - Google compares the strings.
    """
    choices = [latex_to_text(question.get(f"option_{letter}")) for letter in OPTIONS]
    correct_letter = str(question.get("correct_option") or "a").strip().lower()[:1]
    correct = (
        choices[OPTIONS.index(correct_letter)]
        if correct_letter in OPTIONS
        else choices[0]
    )

    grading: dict = {
        "pointValue": 1,
        "correctAnswers": {"answers": [{"value": correct}]},
    }
    explanation = latex_to_text(question.get("explanation"))
    if explanation:
        # Shown after submitting, so a wrong answer teaches something
        grading["whenWrong"] = {"text": explanation[:950]}

    item: dict = {
        "title": latex_to_text(question.get("question_text"))
        or f"Question {index + 1}",
        "questionItem": {},
    }

    # Google fetches sourceUri once, while the form is being built, and then
    # serves its own copy - so a link that expires in an hour is enough.
    image_url = (question.get("image_url") or "").strip()
    if image_url:
        item["questionItem"]["image"] = {
            "sourceUri": image_url,
            "altText": (question.get("image_alt") or "Diagram")[:1900],
        }

    return {
        "createItem": {
            "item": {
                **item,
                "questionItem": {
                    **item["questionItem"],
                    "question": {
                        "required": True,
                        "grading": grading,
                        "choiceQuestion": {
                            "type": "RADIO",
                            "options": _options(question, choices),
                            "shuffle": False,
                        },
                    }
                },
            },
            "location": {"index": index},
        }
    }


class GoogleFormsService:
    """Turns a NISAAB quiz into a shareable Google Form.

    Takes the OAuth client and the refresh token of the Google account that owns
    the forms. Raises :class:`FormsNotConfiguredError` when any of the three is
    missing, so the API can say so plainly instead of failing at Google.
    """

    def __init__(
        self,
        client_id: str = "",
        client_secret: str = "",
        refresh_token: str = "",
    ) -> None:
        if not (client_id and client_secret and refresh_token):
            raise FormsNotConfiguredError(
                "Google Forms needs GOOGLE_OAUTH_CLIENT_ID, "
                "GOOGLE_OAUTH_CLIENT_SECRET and GOOGLE_OAUTH_REFRESH_TOKEN. "
                "Run scripts/admin/authorise_google_forms.py to set them."
            )
        self._client_id = client_id
        self._client_secret = client_secret
        self._refresh_token = refresh_token

    def _access_token(self, client: httpx.Client) -> str:
        """Swap the long-lived refresh token for a short-lived access token.

        Forms are made rarely - a student presses a button - so this runs per
        call rather than caching, which keeps it free of shared state.
        """
        reply = client.post(
            TOKEN_URI,
            data={
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "refresh_token": self._refresh_token,
                "grant_type": "refresh_token",
            },
        )
        if reply.status_code != 200:
            # Expired or revoked. While the OAuth app is in "Testing" publishing
            # status Google expires refresh tokens after about seven days.
            raise FormsNotConfiguredError(
                "The stored Google authorisation is no longer valid "
                f"({reply.status_code}). Run "
                "scripts/admin/authorise_google_forms.py again."
            )
        return reply.json()["access_token"]

    def publish_quiz(
        self,
        title: str,
        questions: list[dict],
        description: str | None = None,
    ) -> PublishedForm:
        """Create the form, mark it a quiz, add the questions and share the link.

        Args:
            title: What the form is called
            questions: Dicts with question_text, option_a..d, correct_option and
                an optional explanation
            description: A line under the title, e.g. the subject and SLO

        Raises:
            ValueError: If there are no questions
            FormsNotConfiguredError: If the stored authorisation has expired
            httpx.HTTPStatusError: If Google refuses a call
        """
        if not questions:
            raise ValueError("A form needs at least one question")

        # The title shows in Drive and on the form itself, both plain text
        title = latex_to_text(title) or "Practice quiz"
        description = latex_to_text(description) or None

        with httpx.Client(timeout=TIMEOUT) as client:
            headers = {
                "Authorization": f"Bearer {self._access_token(client)}",
                "Content-Type": "application/json",
            }

            # create() only accepts the title; everything else is an update
            created = client.post(
                FORMS_API,
                headers=headers,
                json={"info": {"title": title[:300], "documentTitle": title[:300]}},
            )
            created.raise_for_status()
            form_id = created.json()["formId"]

            requests: list[dict] = [
                {
                    "updateSettings": {
                        "settings": {"quizSettings": {"isQuiz": True}},
                        "updateMask": "quizSettings.isQuiz",
                    }
                }
            ]
            if description:
                requests.append(
                    {
                        "updateFormInfo": {
                            "info": {"description": description[:950]},
                            "updateMask": "description",
                        }
                    }
                )
            requests += [_question_item(q, i) for i, q in enumerate(questions)]

            updated = client.post(
                f"{FORMS_API}/{form_id}:batchUpdate",
                headers=headers,
                json={"requests": requests},
            )
            updated.raise_for_status()

            # Anyone with the link may open it; without this only the owner can
            shared = client.post(
                f"{DRIVE_API}/{form_id}/permissions",
                headers=headers,
                json={"role": "reader", "type": "anyone"},
            )
            shared.raise_for_status()

            form = client.get(f"{FORMS_API}/{form_id}", headers=headers)
            form.raise_for_status()
            body = form.json()

        return PublishedForm(
            form_id=form_id,
            responder_url=body.get(
                "responderUri", f"https://docs.google.com/forms/d/{form_id}/viewform"
            ),
            edit_url=f"https://docs.google.com/forms/d/{form_id}/edit",
        )

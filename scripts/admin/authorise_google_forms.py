"""Authorise NISAAB to create Google Forms, once, as a real Google account.

Run it on your own machine (not on Cloud Run), passing the JSON the Cloud
console downloaded when you made the OAuth client:

    python scripts/admin/authorise_google_forms.py path/to/client_secret_*.json

Without that argument it asks for the client ID and secret instead.

It opens a browser, you sign in as the account that should own the forms
(nisaab.imcb@gmail.com), and it stores three secrets in Secret Manager:

    edu-google-oauth-client-id
    edu-google-oauth-client-secret
    edu-google-oauth-refresh-token

The refresh token is never printed and never written to a file. Afterwards run
``bash deploy/gcp/deploy.sh deploy`` so Cloud Run picks the secrets up.

Why this exists
---------------
A service account cannot own a Google Form - it has no Drive storage quota, so
Google answers 500 - and the alternatives (shared drives, domain-wide
delegation) need Google Workspace. See edu_core.services.google_forms.

Before running, create the OAuth client once in the Cloud console:
  1. APIs & Services -> OAuth consent screen -> External, app name NISAAB
  2. Add the owning account under Test users
  3. Add scopes  .../auth/forms.body  and  .../auth/drive.file
  4. Credentials -> Create credentials -> OAuth client ID -> Desktop app

Note: while the consent screen stays in "Testing" publishing status Google
expires refresh tokens after about seven days, so this has to be re-run until
the app is verified. It takes under a minute.
"""

import base64
import getpass
import hashlib
import http.server
import json
import os
import secrets
import socket
import subprocess
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "fbise-tutor-2026")
AUTH_URI = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URI = "https://oauth2.googleapis.com/token"
SCOPES = (
    "https://www.googleapis.com/auth/forms.body "
    "https://www.googleapis.com/auth/drive.file"
)
DEFAULT_SDK = "C:/Program Files (x86)/Google/Cloud SDK/google-cloud-sdk"

SECRET_CLIENT_ID = "edu-google-oauth-client-id"
SECRET_CLIENT_SECRET = "edu-google-oauth-client-secret"
SECRET_REFRESH_TOKEN = "edu-google-oauth-refresh-token"


def gcloud_command() -> list[str]:
    """How to invoke gcloud here.

    On Windows, gcloud.cmd trips over the spaces and brackets in "Program Files
    (x86)", so call the SDK's bundled Python directly - the same trick as
    deploy/gcp/gcloud-win.
    """
    sdk = Path(os.environ.get("CLOUDSDK_ROOT", DEFAULT_SDK))
    bundled = sdk / "platform" / "bundledpython" / "python.exe"
    entry = sdk / "lib" / "gcloud.py"
    if bundled.is_file() and entry.is_file():
        return [str(bundled), str(entry)]
    return ["gcloud"]


GCLOUD = gcloud_command()


def put_secret(name: str, value: str) -> None:
    """Create the secret if needed and add this value as a new version.

    The value goes in over stdin so it never appears in a command line, where
    other processes on the machine could read it.
    """
    describe = subprocess.run(
        [*GCLOUD, "secrets", "describe", name, "--project", PROJECT_ID],
        capture_output=True,
    )
    if describe.returncode != 0:
        created = subprocess.run(
            [
                *GCLOUD, "secrets", "create", name,
                "--replication-policy", "automatic",
                "--project", PROJECT_ID,
            ],
            capture_output=True,
            text=True,
        )
        if created.returncode != 0:
            raise SystemExit(f"Could not create secret {name}:\n{created.stderr}")

    added = subprocess.run(
        [
            *GCLOUD, "secrets", "versions", "add", name,
            "--data-file=-", "--project", PROJECT_ID,
        ],
        input=value.encode("utf-8"),
        capture_output=True,
    )
    if added.returncode != 0:
        raise SystemExit(
            f"Could not store secret {name}:\n{added.stderr.decode('utf-8', 'replace')}"
        )
    print(f"  stored {name}")


class _Catcher(http.server.BaseHTTPRequestHandler):
    """Catches the one redirect Google sends back, then gets out of the way."""

    query: dict = {}

    def do_GET(self) -> None:  # noqa: N802 - name fixed by BaseHTTPRequestHandler
        _Catcher.query = dict(
            urllib.parse.parse_qsl(urllib.parse.urlparse(self.path).query)
        )
        ok = "code" in _Catcher.query
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        body = (
            "<h2>NISAAB is authorised.</h2><p>You can close this tab.</p>"
            if ok
            else "<h2>Authorisation was refused.</h2><p>Nothing was stored.</p>"
        )
        self.wfile.write(
            f"<html><body style='font-family:system-ui;padding:3rem'>{body}"
            "</body></html>".encode()
        )

    def log_message(self, *args) -> None:
        """Stay quiet; the script prints its own progress."""


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def authorise(client_id: str, client_secret: str) -> str:
    """Run the loopback OAuth flow and return the refresh token."""
    # PKCE: proves the code came back to the process that asked for it
    verifier = secrets.token_urlsafe(64)
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        .decode()
        .rstrip("=")
    )

    port = free_port()
    redirect_uri = f"http://localhost:{port}"
    server = http.server.HTTPServer(("127.0.0.1", port), _Catcher)

    url = f"{AUTH_URI}?" + urllib.parse.urlencode(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": SCOPES,
            # offline + consent together are what actually yield a refresh token
            "access_type": "offline",
            "prompt": "consent",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
    )

    print("\nOpening your browser. Sign in as the account that should own the forms.")
    print("If it does not open, paste this into a browser:\n")
    print(f"  {url}\n")
    threading.Thread(target=webbrowser.open, args=(url,), daemon=True).start()
    server.handle_request()
    server.server_close()

    if "code" not in _Catcher.query:
        raise SystemExit(
            "No authorisation code came back "
            f"({_Catcher.query.get('error', 'cancelled')}). Nothing was stored."
        )

    request = urllib.request.Request(
        TOKEN_URI,
        data=urllib.parse.urlencode(
            {
                "code": _Catcher.query["code"],
                "client_id": client_id,
                "client_secret": client_secret,
                "code_verifier": verifier,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            }
        ).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as reply:
            payload = json.load(reply)
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace")[:500]
        raise SystemExit(f"Google refused the exchange ({error.code}):\n{detail}")

    token = payload.get("refresh_token")
    if not token:
        raise SystemExit(
            "Google returned no refresh token. This happens when the account has\n"
            "already authorised this client; remove NISAAB at\n"
            "https://myaccount.google.com/permissions and run this again."
        )
    return token


def read_client_file(path: Path) -> tuple[str, str]:
    """Pull the client ID and secret out of the JSON the Cloud console hands you.

    It holds a single object keyed "installed" (Desktop app) or "web". Reading
    it beats retyping the secret, which should not pass through a terminal.
    """
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise SystemExit(f"Could not read {path}:\n  {error}")

    block = payload.get("installed") or payload.get("web") or {}
    client_id = str(block.get("client_id", "")).strip()
    client_secret = str(block.get("client_secret", "")).strip()
    if not (client_id and client_secret):
        raise SystemExit(
            f"{path.name} is not an OAuth client file: no installed/web section\n"
            "with a client_id and client_secret. Download it again from\n"
            "Credentials -> your OAuth client -> Download JSON."
        )
    return client_id, client_secret


def main() -> int:
    print(f"Authorising NISAAB to create Google Forms (project {PROJECT_ID}).")

    if len(sys.argv) > 1:
        source = Path(sys.argv[1])
        client_id, client_secret = read_client_file(source)
        print(f"Read the OAuth client from {source.name}")
    else:
        print("Paste the OAuth client, or re-run with the path to the JSON")
        print("the Cloud console downloaded.\n")
        client_id = input("  Client ID     : ").strip()
        # Hidden, so the secret stays out of the terminal scrollback
        client_secret = getpass.getpass("  Client secret : ").strip()
        if not client_id or not client_secret:
            raise SystemExit("Both the client ID and the client secret are needed.")

    refresh_token = authorise(client_id, client_secret)
    print("\nAuthorised. Storing the three secrets...")
    put_secret(SECRET_CLIENT_ID, client_id)
    put_secret(SECRET_CLIENT_SECRET, client_secret)
    put_secret(SECRET_REFRESH_TOKEN, refresh_token)

    print("\nDone. The refresh token was not printed anywhere.")
    print("Now run:\n")
    print("  bash deploy/gcp/deploy.sh deploy\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

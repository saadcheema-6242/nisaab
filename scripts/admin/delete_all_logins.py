"""Delete every sign-in from Identity Platform. There is no undo.

Run with:
    python scripts/admin/delete_all_logins.py --yes
    python scripts/admin/delete_all_logins.py --yes --keep me@example.com

Wiping the database removes what students made; it does not remove how they
get in. Those logins stay in Identity Platform, so anyone with an old password
signs back in and is handed a brand new, empty account. This is the other
half, and the Firebase console will not do it in bulk.

Keep yourself with --keep, or you will have to sign up again - and since the
API now wants a confirmed address, you would be locked out of your own admin
page until the new one is verified.

Runs on your own machine against your gcloud login, not on Cloud Run.
"""

import json
import subprocess
import sys
import urllib.error
import urllib.request

PROJECT_ID = "fbise-tutor-2026"
BASE = f"https://identitytoolkit.googleapis.com/v1/projects/{PROJECT_ID}"
# accounts:batchDelete takes at most a thousand at a time
BATCH = 500


def token() -> str:
    """A short-lived access token from the gcloud login already on this machine."""
    out = subprocess.run(
        ["gcloud", "auth", "print-access-token"],
        capture_output=True, text=True, shell=True,
    )
    value = (out.stdout or "").strip()
    if not value:
        raise SystemExit(
            "Could not get an access token. Run: gcloud auth login\n"
            + (out.stderr or "").strip()
        )
    return value


def call(path: str, body: dict, access: str) -> dict:
    request = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {access}",
            "Content-Type": "application/json",
            "x-goog-user-project": PROJECT_ID,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as reply:
            return json.loads(reply.read() or b"{}")
    except urllib.error.HTTPError as error:
        raise SystemExit(f"{path} failed ({error.code}):\n{error.read().decode()[:400]}")


def everyone(access: str) -> list[dict]:
    """Every account, a page at a time."""
    found, page = [], None
    while True:
        body = {"maxResults": 1000}
        if page:
            body["nextPageToken"] = page
        reply = call("/accounts:batchGet", body, access)
        found += reply.get("users") or []
        page = reply.get("nextPageToken")
        if not page:
            return found


def main() -> int:
    if "--yes" not in sys.argv:
        print("Refusing to run without --yes. This permanently deletes every sign-in.")
        return 1

    keep = {
        sys.argv[i + 1].strip().lower()
        for i, a in enumerate(sys.argv)
        if a == "--keep" and i + 1 < len(sys.argv)
    }

    access = token()
    users = everyone(access)
    if not users:
        print("No sign-ins to delete.")
        return 0

    doomed, kept = [], []
    for user in users:
        email = (user.get("email") or "").strip().lower()
        (kept if email and email in keep else doomed).append(user)

    print(f"{len(users)} sign-in(s) found.")
    for user in kept:
        print(f"  keeping  {user.get('email') or '(no email)'}")
    for user in doomed:
        verified = "verified" if user.get("emailVerified") else "unverified"
        print(f"  deleting {user.get('email') or '(no email)'}  ({verified})")

    if not doomed:
        print("\nNothing to delete.")
        return 0

    ids = [u["localId"] for u in doomed]
    removed = 0
    for start in range(0, len(ids), BATCH):
        chunk = ids[start:start + BATCH]
        reply = call(
            "/accounts:batchDelete",
            {"localIds": chunk, "force": True},
            access,
        )
        failed = reply.get("errors") or []
        removed += len(chunk) - len(failed)
        for problem in failed:
            print(f"  could not delete index {problem.get('index')}: {problem.get('message')}")

    print(f"\nDone. {removed} sign-in(s) deleted, {len(kept)} kept.")
    print(
        "\nThe database rows are a separate thing - clear those from the "
        "Accounts page if you have not already."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

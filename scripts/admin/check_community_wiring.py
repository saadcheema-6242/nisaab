"""Check that the class room's moderation is actually wired up.

Run with:
    python scripts/admin/check_community_wiring.py

The rules are checked elsewhere, against the functions themselves. This is
the other half: that the service calls them, that the routes exist, that
every one is behind the right guard, and that the administrator's routes are
behind the administrator check.

A rule that is correct and never called is worse than no rule, because the
tests for it pass. So this reads the source and asserts the connections.

No database, no network, no imports of the API (which needs pgvector,
openai and langchain to load).
"""

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
API = ROOT / "src/edu-api"
CORE = ROOT / "src/shared/core/src/edu_core"

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}" + (f"  -- {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(name)


service = (CORE / "services/community.py").read_text(encoding="utf-8")
queue = (CORE / "services/moderation_queue.py").read_text(encoding="utf-8")
router = (API / "routers/community.py").read_text(encoding="utf-8")
admin = (API / "routers/admin.py").read_text(encoding="utf-8")
deps = (API / "dependencies.py").read_text(encoding="utf-8")
usage = (CORE / "services/usage.py").read_text(encoding="utf-8")
config = (API / "config.py").read_text(encoding="utf-8")

print("contact details are refused before anything is stored")
check("the service calls the finder", "find_personal_details(" in service)
check("and tells the student why", "refusal_message(" in service)
check("the poll question is checked too",
      "find_personal_details(poll_question" in service)
check("and every option",
      "for option in poll_options" in service)
# A post rejected after its files are written leaves them in the bucket.
body_at = service.find("found = find_personal_details(said)")
store_at = service.find("self._store(")
check("the check runs before anything is uploaded",
      0 < body_at < store_at,
      "a rejected post must not leave files behind")

print()
print("uploads are checked, and the bytes have the last word")
check("the service checks each file", "check_upload(" in service)
check("and how many there are", "check_attachment_count(" in service)
check("the first bytes are passed in, not just the claim",
      "data[:16]" in service)
check("checking happens before the post row exists",
      service.find("checked.append(") < service.find("db.add(post)"))

print()
print("the model flags, and never deletes")
check("the service asks for a review", "self._review(" in service)
check("it stores the finding", "post.review_finding = review.finding" in service)
check("and the severity, which the queue sorts by",
      "post.review_severity = review.severity" in service)
check("nothing in the service deletes on a finding",
      "db.delete" not in service.split("def _review")[1].split("def ")[0])

print()
print("a failing model never loses a post")
review_fn = service.split("def _review(")[1].split("\n    def ")[0]
check("every failure returns None", "return None" in review_fn)
check("it catches broadly, on purpose", "except Exception" in review_fn)
check("and says so in the log", "logger.warning" in review_fn)
check("an unconfigured reviewer is not an error",
      "if self.reviewer is None" in review_fn)

print()
print("the author is warned once, not every time the page opens")
check("the warning is stored on the post", "post.warning_text = warning" in service)
check("with the moment it was sent", "post.warned_at =" in service)
check("only unseen warnings are shown",
      "CommunityPost.warning_seen_at.is_(None)" in service)
check("and marking them seen is possible", "def mark_warnings_seen" in service)

print()
print("distress is handled differently from a telling-off")
check("the warning carries whether it is support",
      "is_support=post.review_finding == SELF_HARM" in service)

print()
print("students can report, once each")
check("the service has report_post", "def report_post" in service)
check("reporting twice is quietly ignored, not an error",
      "if already is not None:\n                return" in service)
check("a reported post goes back in the queue",
      "post.reviewed_at = None" in service)
check("the report route exists", '@router.post("/{post_id}/report"' in router)

print()
print("an administrator can delete anything, and nobody else can")
check("the queue service can delete", "def delete_post" in queue)
check("the admin route exists", '@router.delete("/moderation/{post_id}"' in admin)
check("a student can only delete their own",
      "CommunityPost.user_id == user_id" in service.split("def delete_post")[1][:400])

print()
print("every community route requires a signed-in student")
tree = ast.parse(router)
routes = [
    node for node in tree.body
    if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef))
    and any(
        isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute)
        and d.func.attr in ("get", "post", "delete", "patch", "put")
        for d in node.decorator_list
    )
]
check("there are routes to check", len(routes) >= 7, str(len(routes)))
for node in routes:
    args = [a.arg for a in node.args.args + node.args.kwonlyargs]
    check(f"{node.name} takes current_user", "current_user" in args)

print()
print("every moderation route is behind the administrator check")
admin_tree = ast.parse(admin)
for node in admin_tree.body:
    if not isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
        continue
    paths = [
        d.args[0].value
        for d in node.decorator_list
        if isinstance(d, ast.Call) and d.args
        and isinstance(d.args[0], ast.Constant)
        and isinstance(d.args[0].value, str)
    ]
    if not any("moderation" in p for p in paths):
        continue
    source = ast.get_source_segment(admin, node) or ""
    check(f"{node.name} requires an administrator", "require_admin" in source)

print()
print("the room never leaks what it should not")
post_dto = (CORE / "schemas/community.py").read_text(encoding="utf-8")
room_part = post_dto.split("class CommunityPostDto")[1].split("class CommunityWarningDto")[0]
for leaked in ("review_finding", "severity", "report_count", "author_email"):
    check(f"a post does not carry {leaked}", leaked not in room_part)
check("an administrator's item does carry the email",
      "author_email" in post_dto.split("class ModerationItemDto")[1])

print()
print("posting is rate limited, like everything else expensive")
check("the usage service knows about posts", '"community_post"' in usage)
check("it counts them", "usage.community_posts_today += 1" in usage)
check("there is a limit to compare against",
      "max_community_posts_per_day" in usage)
check("the setting exists", "max_community_posts_per_day: int" in config)
check("the JSON route counts before posting",
      'usage_type="community_post"' in router)
check("and so does the upload route",
      router.count('usage_type="community_post"') >= 2,
      "a student could post files without being counted")

print()
print("the services are constructed with what they need")
check("the community service gets storage", "storage=get_storage()" in deps)
check("and a reviewer", "reviewer=_community_reviewer()" in deps)
check("and the daily limit", "daily_posts=settings.max_community_posts_per_day" in deps)
check("no model configured means no reviewer, not a crash",
      "if not is_llm_configured():\n            return None" in deps)
check("the moderation queue is available", "def get_moderation_queue_service" in deps)

print()
print("deleting a post takes its files with it")
check("the student's delete removes files", "_drop_files(" in service)
check("the administrator's delete does too", "self.storage.delete(paths)" in queue)
check("a failed file delete does not keep the post",
      "logger.warning" in queue.split("def delete_post")[1])

print()
print("downloads are checked against the room, not just the link")
check("a download goes through the service", "def attachment_bytes" in service)
check("which filters by the reader's own room",
      "CommunityPost.grade == grade" in service.split("def attachment_bytes")[1])
check("the route exists", '@router.get("/attachments/{attachment_id}"' in router)

print()
if failures:
    print(f"{len(failures)} failed:")
    for name in failures:
        print(f"  - {name}")
    sys.exit(1)
print("all checks passed")

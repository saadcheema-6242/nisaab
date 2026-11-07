"""Check the migration against the models before it touches a database.

Run with:
    python scripts/admin/check_migration.py

A migration is the one piece of code that cannot be half-applied and walked
away from. It runs inside the deploy, before the services come up, so a
mistake in it stops the deploy with the database part-changed.

The mistake this was written for was mine: the new column was added to
"usage_records", and the table is called "user_usage". Nothing locally would
have caught it, because the local environment has no pgvector and the models
cannot be imported. The deploy would have failed at the migration step.

So this reads both files as text and compares them. No database, no
SQLAlchemy, no pgvector.
"""

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODELS = ROOT / "src/shared/db/src/edu_db/models.py"
VERSIONS = ROOT / "src/shared/db/src/edu_db/alembic/versions"

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}" + (f"  -- {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(name)


# ---- what the models say exists -------------------------------------------
source = MODELS.read_text(encoding="utf-8")
tree = ast.parse(source)

tables: dict[str, set[str]] = {}
class_table: dict[str, str] = {}
for node in ast.walk(tree):
    if not isinstance(node, ast.ClassDef):
        continue
    table = None
    columns: set[str] = set()
    for stmt in node.body:
        if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
            if stmt.target.id == "__tablename__":
                table = ast.literal_eval(stmt.value)
            else:
                columns.add(stmt.target.id)
        elif isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if isinstance(target, ast.Name) and target.id == "__tablename__":
                    table = ast.literal_eval(stmt.value)
    if table:
        tables[table] = columns
        class_table[node.name] = table

print(f"models define {len(tables)} tables")

# ---- the migration chain --------------------------------------------------
revisions: dict[str, Path] = {}
downs: dict[str, str | None] = {}
for path in VERSIONS.glob("*.py"):
    text = path.read_text(encoding="utf-8", errors="ignore")
    rev = re.search(r"^revision(?::\s*str)?\s*=\s*['\"]([^'\"]+)", text, re.M)
    down = re.search(
        r"^down_revision(?::\s*[^=]+)?\s*=\s*['\"]([^'\"]+)", text, re.M
    )
    if rev:
        revisions[rev.group(1)] = path
        downs[rev.group(1)] = down.group(1) if down else None

print()
print("the chain has exactly one head")
heads = [r for r in revisions if r not in set(downs.values())]
check("one head, not several", len(heads) == 1, f"heads: {heads}")
for rev, parent in downs.items():
    if parent is not None:
        check(
            f"{rev} points at a revision that exists",
            parent in revisions,
            f"missing parent {parent}",
        )

print()
print("every table a migration touches is a table the models define")
# Tables created by a migration and never modelled are legitimate only if
# nothing reads them through SQLAlchemy. Every one here should be modelled.
# create_index takes the index name first and the table second, so it needs
# its own pattern. Reading the first string for all of them reported every
# index in the repository as an unknown table, which is the kind of noise
# that gets a check switched off.
TOUCH = re.compile(
    r'op\.(add_column|drop_column|alter_column|create_table|drop_table)'
    r'\(\s*\n?\s*["\']([a-z_]+)["\']'
)
TOUCH_INDEX = re.compile(
    r'op\.(create_index)\(\s*\n?\s*["\'][a-z_]+["\'],\s*\n?\s*["\']([a-z_]+)["\']'
)
# Tables managed by alembic itself.
KNOWN_OTHER = {"alembic_version"}

# A table created and then dropped by a later migration is correctly absent
# from the models. Collected first, so history does not read as a fault.
dropped_later: set[str] = set()
for path in VERSIONS.glob("*.py"):
    upgrade_text = path.read_text(encoding="utf-8", errors="ignore").split(
        "def downgrade()"
    )[0]
    dropped_later.update(
        re.findall(r'op\.drop_table\(\s*["\']([a-z_]+)["\']', upgrade_text)
    )

# study_sessions predates this check. It is still in the database and
# flashcard_groups.study_session_id still points at it, but nothing models
# it, so nothing reads it through SQLAlchemy. Listed rather than ignored, so
# it stays visible as something to tidy up, without failing the check over a
# decision made long ago.
KNOWN_ORPHANS = {"study_sessions"}

for rev, path in sorted(revisions.items()):
    text = path.read_text(encoding="utf-8", errors="ignore")
    # Only the upgrade: a downgrade legitimately names things it is removing.
    upgrade_only = text.split("def downgrade()")[0]
    for op_name, table in (
        TOUCH.findall(upgrade_only) + TOUCH_INDEX.findall(upgrade_only)
    ):
        if table in KNOWN_OTHER or table in dropped_later or table in KNOWN_ORPHANS:
            continue
        if op_name in ("drop_table", "drop_column"):
            continue
        if table not in tables:
            check(
                f"{path.name}: {op_name} on '{table}'",
                False,
                "no model has this __tablename__",
            )

check("no migration names a table the models do not have", not failures)
if KNOWN_ORPHANS:
    print(f"  note: {', '.join(sorted(KNOWN_ORPHANS))} exists in the database "
          "with no model; nothing reads it, worth tidying one day")

print()
print("the newest migration's columns exist on the model")
head = heads[0] if len(heads) == 1 else None
if head:
    text = revisions[head].read_text(encoding="utf-8", errors="ignore")
    print(f"  head is {revisions[head].name}")
    added = re.findall(
        r'op\.add_column\(\s*\n?\s*["\']([a-z_]+)["\'],\s*\n?\s*sa\.Column\(\s*\n?\s*["\']([a-z_]+)["\']',
        text,
    )
    for table, column in added:
        known = tables.get(table)
        check(
            f"{table}.{column}",
            known is not None and column in known,
            "table unknown" if known is None else f"not on the model ({sorted(known)[:6]}...)",
        )
    created = re.findall(
        r'op\.create_table\(\s*\n?\s*["\']([a-z_]+)["\']', text
    )
    for table in created:
        check(f"created table '{table}' is modelled", table in tables)

print()
print("upgrade and downgrade are mirror images")
if head:
    text = revisions[head].read_text(encoding="utf-8", errors="ignore")
    up = text.split("def upgrade()")[1].split("def downgrade()")[0]
    down = text.split("def downgrade()")[1]
    for table in re.findall(r'op\.create_table\(\s*\n?\s*["\']([a-z_]+)["\']', up):
        check(f"created '{table}' is dropped again", f'"{table}"' in down)
    added_cols = re.findall(
        r'op\.add_column\(\s*\n?\s*["\']([a-z_]+)["\'],\s*\n?\s*sa\.Column\(\s*\n?\s*["\']([a-z_]+)["\']',
        up,
    )
    for table, column in added_cols:
        check(f"added {table}.{column} is dropped again", f'"{column}"' in down)

print()
if failures:
    print(f"{len(failures)} failed:")
    for name in failures:
        print(f"  - {name}")
    sys.exit(1)
print("all checks passed")

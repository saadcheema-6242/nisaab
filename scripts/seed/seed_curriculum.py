"""Load the FBISE FSc curriculum into the database.

Creates the FSc subjects for grades XI and XII (as "coming soon"), then
loads every reviewed SLO file in scripts/seed/data/ and marks those grade
subjects "available". Safe to run again: rows are matched by code and
updated; SLOs no longer in a file are removed.

Usage (from the repository root, with DATABASE_URL set):
    uv run --package edu-worker python scripts/seed/seed_curriculum.py
On Google Cloud it runs as the edu-seed Cloud Run job (deploy/gcp/deploy.sh seed).
"""

import json
import os
from pathlib import Path

from edu_db.models import CurriculumDomain, GradeSubject, Slo, Subject
from edu_db.session import get_session_factory, init_db

DATA_DIR = Path(__file__).resolve().parent / "data"
SCHEME = "ISS-2024"
CURRICULUM = "NCP 2022-23"
GRADES = [11, 12]
SUBJECTS = [
    {"code": "PHY", "name": "Physics", "has_practical": True},
    {"code": "CHEM", "name": "Chemistry", "has_practical": True},
    {"code": "BIO", "name": "Biology", "has_practical": True},
    {"code": "MATH", "name": "Mathematics", "has_practical": False},
    {"code": "CS", "name": "Computer Science", "has_practical": True},
]


def upsert_catalog(db) -> dict[tuple[str, int], GradeSubject]:
    grade_subjects = {}
    for order, fields in enumerate(SUBJECTS):
        subject = db.query(Subject).filter(Subject.code == fields["code"]).first()
        if subject is None:
            subject = Subject(code=fields["code"])
            db.add(subject)
        subject.name = fields["name"]
        subject.has_practical = fields["has_practical"]
        subject.sort_order = order
        db.flush()

        for grade in GRADES:
            grade_subject = (
                db.query(GradeSubject)
                .filter(
                    GradeSubject.subject_id == subject.id,
                    GradeSubject.grade == grade,
                    GradeSubject.scheme == SCHEME,
                )
                .first()
            )
            if grade_subject is None:
                grade_subject = GradeSubject(
                    subject_id=subject.id,
                    grade=grade,
                    scheme=SCHEME,
                    curriculum=CURRICULUM,
                    status="coming_soon",
                )
                db.add(grade_subject)
                db.flush()
            grade_subjects[(fields["code"], grade)] = grade_subject
    return grade_subjects


def load_slos(db, grade_subject: GradeSubject, data: dict) -> tuple[int, int]:
    grade_subject.curriculum = data["curriculum"]
    grade_subject.source_url = data["source_url"]

    domains = {d.code: d for d in grade_subject.domains}
    for order, fields in enumerate(data["domains"]):
        domain = domains.get(fields["code"])
        if domain is None:
            domain = CurriculumDomain(grade_subject_id=grade_subject.id, code=fields["code"])
            db.add(domain)
            domains[fields["code"]] = domain
        domain.name = fields["name"]
        domain.sort_order = order
    db.flush()

    existing = {
        slo.code: slo
        for slo in db.query(Slo).filter(Slo.grade_subject_id == grade_subject.id)
    }
    seen = set()
    for order, fields in enumerate(data["slos"]):
        slo = existing.get(fields["code"])
        if slo is None:
            slo = Slo(grade_subject_id=grade_subject.id, code=fields["code"])
            db.add(slo)
        slo.domain_id = domains[fields["domain"]].id
        slo.content_area = fields["content_area"]
        slo.description = fields["description"]
        slo.assessment_form = fields["assessment_form"]
        slo.cognitive_levels = fields["cognitive_levels"]
        slo.periods = fields["periods"]
        slo.sort_order = order
        seen.add(fields["code"])

    removed = 0
    for code, slo in existing.items():
        if code not in seen:
            db.delete(slo)
            removed += 1
    for code, domain in domains.items():
        if code not in {d["code"] for d in data["domains"]}:
            db.delete(domain)

    grade_subject.status = "available"
    return len(seen), removed


def main() -> None:
    init_db(os.environ["DATABASE_URL"])
    with get_session_factory()() as db:
        grade_subjects = upsert_catalog(db)
        for path in sorted(DATA_DIR.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            key = (data["subject"]["code"], data["grade"])
            if key not in grade_subjects:
                raise SystemExit(f"{path.name}: unknown subject/grade {key}")
            count, removed = load_slos(db, grade_subjects[key], data)
            print(f"{path.name}: {count} SLOs loaded, {removed} removed")
        db.commit()

        for (code, grade), grade_subject in sorted(grade_subjects.items()):
            print(f"{code} {grade}: {grade_subject.status}")


if __name__ == "__main__":
    main()

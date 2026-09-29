"""Pre-generate shared content for a subject's examined SLOs: explainers, MCQs, SRQs.

Items are saved as drafts in ``content_items`` for a subject teacher to review.
Safe to run again: SLOs that already have enough non-rejected items are skipped.

Usage (from the repository root, with DATABASE_URL and an AI provider configured):
    uv run --package edu-worker python scripts/content/generate_bank.py --subject PHY --grade 11 --domains B
On Google Cloud it runs as the edu-content Cloud Run job:
    deploy/gcp/deploy.sh content --subject PHY --grade 11 --domains B
"""

import argparse
import asyncio
import os
import sys
import time

from edu_ai.agents.bank_agent import generate_explainer, generate_mcqs
from edu_ai.agents.slo_context import load_slo
from edu_ai.agents.srq_agent import generate_srq
from edu_ai.llm import GENERATION, create_chat_model
from edu_db.models import ContentItem, CurriculumDomain, GradeSubject, Slo, Subject
from edu_db.session import get_session_factory, init_db

KINDS = ("explainer", "mcq", "srq")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--subject", required=True, help="Subject code, e.g. PHY")
    parser.add_argument("--grade", type=int, required=True, help="11 or 12")
    parser.add_argument("--domains", default="", help="Domain letters, e.g. B or BC (default: all)")
    parser.add_argument("--kinds", default="explainer+mcq+srq", help="Any of explainer, mcq, srq joined by +")
    parser.add_argument("--mcq-count", type=int, default=5, help="MCQs per SLO")
    parser.add_argument("--limit", type=int, default=0, help="Only the first N SLOs (for a trial run)")
    parser.add_argument("--concurrency", type=int, default=4, help="Parallel AI requests")
    return parser.parse_args()


def existing_counts(db, grade_subject_id: str) -> dict[tuple[str, str], int]:
    counts: dict[tuple[str, str], int] = {}
    rows = db.query(ContentItem.slo_code, ContentItem.kind).filter(
        ContentItem.grade_subject_id == grade_subject_id,
        ContentItem.review_status != "rejected",
    )
    for code, kind in rows:
        counts[(code, kind)] = counts.get((code, kind), 0) + 1
    return counts


async def main() -> None:
    args = parse_args()
    kinds = [k for k in args.kinds.split("+") if k]
    if unknown := set(kinds) - set(KINDS):
        sys.exit(f"Unknown kinds: {', '.join(sorted(unknown))}")

    init_db(os.environ["DATABASE_URL"])
    Session = get_session_factory()
    with Session() as db:
        grade_subject = (
            db.query(GradeSubject)
            .join(Subject)
            .filter(Subject.code == args.subject.upper(), GradeSubject.grade == args.grade)
            .one()
        )
        query = (
            db.query(Slo)
            .join(CurriculumDomain, Slo.domain_id == CurriculumDomain.id)
            .filter(Slo.grade_subject_id == grade_subject.id, Slo.assessment_form == "summative")
            .order_by(CurriculumDomain.sort_order, Slo.sort_order)
        )
        if args.domains:
            query = query.filter(CurriculumDomain.code.in_(list(args.domains.upper())))
        codes = [slo.code for slo in query]
        if args.limit:
            codes = codes[: args.limit]
        slos = {code: load_slo(db, code, grade_subject_id=grade_subject.id) for code in codes}
        have = existing_counts(db, grade_subject.id)
        grade_subject_id = grade_subject.id

    needed = {"explainer": 1, "mcq": args.mcq_count, "srq": 1}
    tasks = [
        (code, kind)
        for code in codes
        for kind in kinds
        if have.get((code, kind), 0) < needed[kind]
    ]
    print(f"{len(codes)} examined SLOs, {len(tasks)} items to generate ({', '.join(kinds)})")

    llm = create_chat_model(task=GENERATION, temperature=0.5)
    semaphore = asyncio.Semaphore(args.concurrency)
    stats = {"saved": 0, "failed": 0}

    async def run(code: str, kind: str) -> None:
        slo = slos[code]
        async with semaphore:
            try:
                if kind == "explainer":
                    explainer = await generate_explainer(llm, slo)
                    payloads = [explainer.model_dump()]
                elif kind == "mcq":
                    missing = needed["mcq"] - have.get((code, "mcq"), 0)
                    payloads = (await generate_mcqs(llm, slo, missing))[:missing]
                else:
                    srq = await generate_srq(llm, slo, "en")
                    payloads = [
                        {
                            "question": srq.question,
                            "marks": srq.marks,
                            "model_answer": srq.model_answer,
                            "rubric": [p.model_dump() for p in srq.rubric],
                            "cognitive_level": (srq.cognitive_level or "").strip().upper()[:1] or None,
                        }
                    ]
            except Exception as e:  # keep going; a re-run fills the gaps
                stats["failed"] += 1
                print(f"  FAIL {code} {kind}: {e}")
                return

        with Session() as db:
            for payload in payloads:
                db.add(
                    ContentItem(
                        grade_subject_id=grade_subject_id,
                        slo_code=code,
                        kind=kind,
                        payload=payload,
                    )
                )
            db.commit()
        stats["saved"] += len(payloads)
        print(f"  ok   {code} {kind} ({len(payloads)})")

    start = time.time()
    await asyncio.gather(*(run(code, kind) for code, kind in tasks))
    print(
        f"Done in {time.time() - start:.0f}s: {stats['saved']} items saved, "
        f"{stats['failed']} failed (run again to retry)"
    )
    if stats["failed"]:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

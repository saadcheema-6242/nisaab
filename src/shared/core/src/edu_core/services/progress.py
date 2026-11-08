"""Student progress per subject: mastery by domain, weak SLOs and a predicted grade.

The predicted grade only uses examined (summative) SLOs the student has practised,
each weighted by its teaching periods (a proxy for its weight in the paper). It is
shown with how much of the syllabus it covers, so it reads as an estimate.
"""

from contextlib import contextmanager

from edu_db.models import (
    CurriculumDomain,
    GradeSubject,
    PracticeRecord,
    Project,
    Slo,
)
from edu_db.session import get_session_factory
from sqlalchemy.orm import joinedload

from edu_core.grading import grade_for
from edu_core.mastery import SELF_RATED_WEIGHT, slo_mastery
from edu_core.progress_trend import (
    active_days,
    answers_this_week,
    cognitive_split,
    streaks,
    trend,
    weakest_level,
)
from edu_core.schemas.progress import (
    ActivityDayDto,
    CognitiveLevelDto,
    ConsistencyDto,
    DomainProgressDto,
    PredictedGradeDto,
    ProgressDto,
    ProgressGraphsDto,
    ProgressSloDto,
    SubjectGraphsDto,
    SubjectProgressDto,
    TrendPointDto,
    WeakestLevelDto,
)

WEAK_BELOW = 0.8


class ProgressService:
    """Service for the student's progress dashboard."""

    def get_progress(self, user_id: str) -> ProgressDto:
        with self._get_db_session() as db:
            workspaces = (
                db.query(Project)
                .options(joinedload(Project.grade_subject).joinedload(GradeSubject.subject))
                .filter(Project.owner_id == user_id, Project.kind == "subject_workspace")
                .order_by(Project.created_at)
                .all()
            )
            subjects = []
            for project in workspaces:
                grade_subject = project.grade_subject
                if grade_subject is None:
                    continue
                subjects.append(self._subject_progress(db, user_id, project, grade_subject))
            return ProgressDto(subjects=subjects)

    def _subject_progress(
        self, db, user_id: str, project: Project, grade_subject: GradeSubject
    ) -> SubjectProgressDto:
        rows = (
            db.query(Slo, CurriculumDomain)
            .join(CurriculumDomain, Slo.domain_id == CurriculumDomain.id)
            .filter(Slo.grade_subject_id == grade_subject.id)
            .order_by(CurriculumDomain.sort_order, Slo.sort_order)
            .all()
        )
        base = SubjectProgressDto(
            project_id=project.id,
            grade_subject_id=grade_subject.id,
            subject_code=grade_subject.subject.code,
            name=project.name,
            has_slos=bool(rows),
        )
        examined = [(slo, domain) for slo, domain in rows if slo.assessment_form == "summative"]
        if not examined:
            return base

        progress = slo_mastery(db, user_id, (slo.code for slo, _ in examined))
        items = []
        for slo, domain in examined:
            attempts, mastery = progress.get(slo.code, (0, None))
            items.append(
                (
                    slo,
                    domain,
                    ProgressSloDto(
                        code=slo.code,
                        description=slo.description,
                        domain_code=domain.code,
                        mastery=mastery,
                        attempts=attempts,
                    ),
                )
            )
        practised = [(slo, dto) for slo, _, dto in items if dto.mastery is not None]

        domains = []
        for domain in grade_subject.domains:
            in_domain = [dto for _, d, dto in items if d.id == domain.id]
            if not in_domain:
                continue
            done = [dto.mastery for dto in in_domain if dto.mastery is not None]
            domains.append(
                DomainProgressDto(
                    code=domain.code,
                    name=domain.name,
                    examined_count=len(in_domain),
                    practised_count=len(done),
                    mastery=round(sum(done) / len(done), 3) if done else None,
                )
            )

        weakest = sorted(
            (dto for _, dto in practised if dto.mastery < WEAK_BELOW),
            key=lambda dto: dto.mastery,
        )[:5]
        suggested = [
            dto
            for slo, _, dto in sorted(
                (item for item in items if item[2].mastery is None),
                key=lambda item: -(item[0].periods or 0),
            )
        ][:3]

        base.examined_count = len(items)
        base.practised_count = len(practised)
        base.mastery = (
            round(sum(dto.mastery for _, dto in practised) / len(practised), 3)
            if practised
            else None
        )
        base.predicted = self._predict(items, practised)
        base.domains = domains
        base.weakest = weakest
        base.suggested = suggested
        return base

    @staticmethod
    def _predict(items, practised) -> PredictedGradeDto | None:
        if not practised:
            return None
        weight = lambda slo: slo.periods or 1  # noqa: E731
        total = sum(weight(slo) for slo, _, _ in items)
        covered = sum(weight(slo) for slo, _ in practised)
        percent = 100 * sum(weight(slo) * dto.mastery for slo, dto in practised) / covered
        coverage = covered / total if total else 0.0
        grade, descriptor = grade_for(percent)
        return PredictedGradeDto(
            percent=round(percent),
            grade=grade,
            descriptor=descriptor,
            coverage=round(coverage, 3),
            confidence="high" if coverage >= 0.6 else "medium" if coverage >= 0.2 else "low",
        )


    # ---- the graphs tab --------------------------------------------------

    def get_graphs(self, user_id: str) -> ProgressGraphsDto:
        """Mastery over time, by cognitive level, and how often they practise.

        A second call rather than more fields on get_progress. The overview
        answers "where am I", needs no history, and is what loads first; this
        reads every practice answer the student has ever recorded. Putting
        them together would make the page everyone opens pay for the tab most
        people will not.
        """
        with self._get_db_session() as db:
            workspaces = (
                db.query(Project)
                .options(
                    joinedload(Project.grade_subject).joinedload(GradeSubject.subject)
                )
                .filter(
                    Project.owner_id == user_id,
                    Project.kind == "subject_workspace",
                )
                .order_by(Project.created_at)
                .all()
            )

            # The outcomes the overview counts: summative only. The trend has
            # to be built from the same answers or the two numbers disagree
            # again for a different reason - a student who has practised
            # formative material would see it in the graph and not in the
            # heading above it.
            subject_ids = [
                project.grade_subject_id
                for project in workspaces
                if project.grade_subject_id is not None
            ]
            examined_codes = (
                {
                    code
                    for (code,) in db.query(Slo.code)
                    .filter(
                        Slo.grade_subject_id.in_(subject_ids),
                        Slo.assessment_form == "summative",
                    )
                    .all()
                }
                if subject_ids
                else set()
            )

            # Every answer once, for the whole page. Asking per subject would
            # be one query per workspace plus one for the calendar.
            rows = (
                db.query(
                    PracticeRecord.created_at,
                    PracticeRecord.project_id,
                    PracticeRecord.was_correct,
                    PracticeRecord.score,
                    PracticeRecord.item_type,
                    PracticeRecord.slo_code,
                )
                .filter(PracticeRecord.user_id == user_id)
                .order_by(PracticeRecord.created_at)
                .all()
            )

            by_project: dict[str, list[tuple]] = {}
            everything: list[tuple] = []
            moments: list = []
            for created, project_id, correct, score, item_type, slo_code in rows:
                if created is None:
                    continue
                # Every answer counts towards the streak and the calendar,
                # examined or not: the student turned up and did the work,
                # and that is what those two measure.
                moments.append(created)

                if not slo_code or slo_code not in examined_codes:
                    continue

                value = score if score is not None else (1.0 if correct else 0.0)
                factor = SELF_RATED_WEIGHT if item_type == "flashcard" else 1.0
                # slo_code carried through so the trend can estimate per
                # outcome and average, the way the overview does.
                answer = (created, slo_code, float(value), factor)
                by_project.setdefault(project_id, []).append(answer)
                everything.append(answer)

            subjects = [
                self._subject_graphs(db, user_id, project, by_project)
                for project in workspaces
                if project.grade_subject is not None
            ]

            run = streaks(moments)
            return ProgressGraphsDto(
                subjects=subjects,
                overall_trend=[TrendPointDto(**point) for point in trend(everything)],
                consistency=ConsistencyDto(
                    current_streak=run["current"],
                    longest_streak=run["longest"],
                    days_practised=run["days_practised"],
                    answers_this_week=answers_this_week(moments),
                    last_day=run["last_day"],
                    calendar=[ActivityDayDto(**day) for day in active_days(moments)],
                ),
            )

    def _subject_graphs(
        self, db, user_id: str, project: Project, by_project: dict
    ) -> SubjectGraphsDto:
        grade_subject = project.grade_subject
        answers = by_project.get(project.id, [])
        points = trend(answers)

        # The same SLOs the overview counts: examined only, because the
        # cognitive weighting describes the paper, and a formative SLO is
        # never on it.
        examined = (
            db.query(Slo)
            .filter(
                Slo.grade_subject_id == grade_subject.id,
                Slo.assessment_form == "summative",
            )
            .all()
        )
        mastery_by_code = slo_mastery(db, user_id, (slo.code for slo in examined))
        split = cognitive_split(
            [
                (slo.cognitive_levels or [], mastery_by_code.get(slo.code, (0, None))[1], 1)
                for slo in examined
            ]
        )
        worst = weakest_level(split)

        return SubjectGraphsDto(
            project_id=project.id,
            subject_code=grade_subject.subject.code,
            name=project.name,
            # Taken from the last point of the trend rather than recomputed,
            # so the number beside the graph is the number the graph ends on.
            mastery=points[-1]["mastery"] if points else None,
            trend=[TrendPointDto(**point) for point in points],
            cognitive=[CognitiveLevelDto(**row) for row in split],
            weakest_level=WeakestLevelDto(**worst) if worst else None,
        )

    @contextmanager
    def _get_db_session(self):
        """Context manager for database sessions."""
        SessionLocal = get_session_factory()
        db = SessionLocal()
        try:
            yield db
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

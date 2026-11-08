"""Student profile and onboarding (creates one workspace per FSc subject)."""

from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import uuid4

from edu_db.models import GradeSubject, Project, StudentProfile, Subject
from edu_db.session import get_session_factory
from sqlalchemy.orm import joinedload

from edu_core.exceptions import NotFoundError
from edu_core.group_change import GROUP_SUBJECTS, subjects_for
from edu_core.schemas.profiles import (
    OnboardingResultDto,
    ProfileStateDto,
    StudentProfileDto,
)
from edu_core.schemas.projects import ProjectDto

SCHEME = "ISS-2024"
GRADE_NAMES = {11: ("XI", "HSSC-I"), 12: ("XII", "HSSC-II")}
SUBJECT_WORKSPACE = "subject_workspace"


class ProfileService:
    """Service for the student profile and onboarding."""

    def get_profile_state(self, user_id: str) -> ProfileStateDto:
        """Get the user's profile and whether onboarding is complete."""
        with self._get_db_session() as db:
            profile = db.get(StudentProfile, user_id)
            return ProfileStateDto(
                onboarded=bool(profile and profile.onboarding_completed_at),
                profile=StudentProfileDto.model_validate(profile) if profile else None,
            )

    def complete_onboarding(
        self,
        user_id: str,
        grade: int,
        group_code: str,
        explanation_language: str,
        exam_year: int | None = None,
        all_cohorts: bool = False,
    ) -> OnboardingResultDto:
        """Save the profile and create the missing subject workspaces.

        Running it again (e.g. after moving to grade XII) keeps existing
        workspaces and adds the ones for the new grade or group.

        all_cohorts is for an administrator, who is a student of everything:
        every FSc subject in both years rather than one group's three. They
        still carry a grade and a group, because the class room and the
        timetable are per cohort and something has to be chosen, but their
        subjects are not limited to it. Nothing is archived for them either,
        since there is no group they have left.
        """
        with self._get_db_session() as db:
            profile = db.get(StudentProfile, user_id)
            if profile is None:
                profile = StudentProfile(user_id=user_id)
                db.add(profile)
            profile.grade = grade
            profile.group_code = group_code
            profile.explanation_language = explanation_language
            profile.exam_year = exam_year
            profile.onboarding_completed_at = datetime.now(timezone.utc)

            if not all_cohorts:
                # Subjects this group does not study are hidden first, so a
                # student who switches group stops carrying the old one's
                # papers into their mastery and their study plans.
                self._archive_dropped(db, user_id, grade, group_code)

            if all_cohorts:
                codes = sorted({c for subs in GROUP_SUBJECTS.values() for c in subs})
                grades = [11, 12]
            else:
                codes = GROUP_SUBJECTS[group_code]
                grades = [grade]

            grade_subjects = (
                db.query(GradeSubject)
                .join(Subject)
                .options(joinedload(GradeSubject.subject))
                .filter(
                    GradeSubject.grade.in_(grades),
                    GradeSubject.scheme == SCHEME,
                    Subject.code.in_(codes),
                )
                .all()
            )
            if len(grade_subjects) < len(codes):
                raise NotFoundError(
                    "The FBISE curriculum is not loaded yet (run the seed job)"
                )
            grade_subjects.sort(
                key=lambda gs: (gs.grade, codes.index(gs.subject.code))
            )

            existing = {
                project.grade_subject_id: project
                for project in db.query(Project).filter(
                    Project.owner_id == user_id,
                    Project.kind == SUBJECT_WORKSPACE,
                )
            }
            workspaces = []
            for grade_subject in grade_subjects:
                project = existing.get(grade_subject.id)
                if project is None:
                    project = Project(
                        id=str(uuid4()),
                        owner_id=user_id,
                        kind=SUBJECT_WORKSPACE,
                        grade_subject=grade_subject,
                        name=workspace_name(grade_subject),
                        description=workspace_description(grade_subject),
                        created_at=datetime.now(timezone.utc),
                    )
                    db.add(project)
                project.language_code = explanation_language
                workspaces.append(project)

            db.commit()
            db.refresh(profile)
            return OnboardingResultDto(
                profile=StudentProfileDto.model_validate(profile),
                projects=[project_to_dto(project) for project in workspaces],
            )

    def change_group(self, user_id: str, group_code: str) -> OnboardingResultDto:
        """Move a student to another FSc group, keeping their grade.

        A thin wrapper: onboarding already does the work, and it is the path
        the "Change class or group" button has always used. Having two ways to
        change a group would mean two places to get the archiving right.
        """
        with self._get_db_session() as db:
            profile = db.get(StudentProfile, user_id)
            if profile is None:
                raise NotFoundError("Complete onboarding first")
            grade, language, exam_year = (
                profile.grade,
                profile.explanation_language,
                profile.exam_year,
            )
        return self.complete_onboarding(
            user_id=user_id,
            grade=grade,
            group_code=group_code,
            explanation_language=language,
            exam_year=exam_year,
        )

    @staticmethod
    def _archive_dropped(db, user_id: str, grade: int, group_code: str) -> None:
        """Hide the subjects this group does not study, and restore the ones it does.

        Hidden, never deleted. A student who spent a month on Chemistry notes
        before switching should not lose them to a dropdown, and switching
        back must bring the work with it.

        Only this grade's workspaces are touched. Moving from XI to XII drops
        nothing, and archiving by subject alone would quietly hide last year's
        work the first time anybody moved up.
        """
        wanted = set(subjects_for(group_code))
        now = datetime.now(timezone.utc)
        rows = (
            db.query(Project, Subject.code)
            .join(GradeSubject, Project.grade_subject_id == GradeSubject.id)
            .join(Subject, GradeSubject.subject_id == Subject.id)
            .filter(
                Project.owner_id == user_id,
                Project.kind == SUBJECT_WORKSPACE,
                GradeSubject.grade == grade,
            )
            .all()
        )
        for project, code in rows:
            if code in wanted:
                project.archived_at = None
            else:
                project.archived_at = project.archived_at or now

    def update_profile(
        self,
        user_id: str,
        explanation_language: str | None = None,
        exam_year: int | None = None,
    ) -> StudentProfileDto:
        """Update profile settings; the explanation language also applies to
        the subject workspaces, so the tutor answers in it.

        Raises:
            NotFoundError: If the user has not completed onboarding
        """
        with self._get_db_session() as db:
            profile = db.get(StudentProfile, user_id)
            if profile is None:
                raise NotFoundError("Complete onboarding first")
            if explanation_language is not None:
                profile.explanation_language = explanation_language
                db.query(Project).filter(
                    Project.owner_id == user_id, Project.kind == SUBJECT_WORKSPACE
                ).update({Project.language_code: explanation_language})
            if exam_year is not None:
                profile.exam_year = exam_year
            db.commit()
            db.refresh(profile)
            return StudentProfileDto.model_validate(profile)

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


def workspace_name(grade_subject: GradeSubject) -> str:
    return f"{grade_subject.subject.name} {GRADE_NAMES[grade_subject.grade][0]}"


def workspace_description(grade_subject: GradeSubject) -> str:
    level = GRADE_NAMES[grade_subject.grade][1]
    return f"FBISE {level} {grade_subject.subject.name} · {grade_subject.curriculum or 'NCP 2022-23'}"


def project_to_dto(project: Project) -> ProjectDto:
    return ProjectDto(
        id=project.id,
        owner_id=project.owner_id,
        name=project.name,
        description=project.description,
        language_code=project.language_code,
        kind=project.kind,
        grade_subject_id=project.grade_subject_id,
        subject_code=project.grade_subject.subject.code if project.grade_subject else None,
        created_at=project.created_at,
    )

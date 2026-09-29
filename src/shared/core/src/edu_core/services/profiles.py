"""Student profile and onboarding (creates one workspace per FSc subject)."""

from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import uuid4

from edu_db.models import GradeSubject, Project, StudentProfile, Subject
from edu_db.session import get_session_factory
from sqlalchemy.orm import joinedload

from edu_core.exceptions import NotFoundError
from edu_core.schemas.profiles import (
    OnboardingResultDto,
    ProfileStateDto,
    StudentProfileDto,
)
from edu_core.schemas.projects import ProjectDto

SCHEME = "ISS-2024"
GROUP_SUBJECTS = {
    "PRE_MED": ["PHY", "CHEM", "BIO"],
    "PRE_ENG": ["PHY", "CHEM", "MATH"],
}
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
    ) -> OnboardingResultDto:
        """Save the profile and create the missing subject workspaces.

        Running it again (e.g. after moving to grade XII) keeps existing
        workspaces and adds the ones for the new grade or group.
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

            codes = GROUP_SUBJECTS[group_code]
            grade_subjects = (
                db.query(GradeSubject)
                .join(Subject)
                .options(joinedload(GradeSubject.subject))
                .filter(
                    GradeSubject.grade == grade,
                    GradeSubject.scheme == SCHEME,
                    Subject.code.in_(codes),
                )
                .all()
            )
            if len(grade_subjects) != len(codes):
                raise NotFoundError(
                    "The FBISE curriculum is not loaded yet (run the seed job)"
                )
            grade_subjects.sort(key=lambda gs: codes.index(gs.subject.code))

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

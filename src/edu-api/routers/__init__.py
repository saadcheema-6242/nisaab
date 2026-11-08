from .attempts import router as attempts_router
from .auth import router as auth_router
from .chats import router as chats_router
from .curriculum import router as curriculum_router
from .documents import router as documents_router
from .flashcard_groups import router as flashcard_groups_router
from .mind_maps import router as mind_maps_router
from .notes import router as notes_router
from .papers import router as papers_router
from .practice_records import router as practice_records_router
from .profile import router as profile_router
from .admin import router as admin_router
from .community import router as community_router
from .progress import router as progress_router
from .sessions import router as sessions_router
from .projects import router as projects_router
from .quizzes import router as quizzes_router
from .review import router as review_router
from .srq import router as srq_router
from .study_plans import study_plans_router
from .usage import router as usage_router
from .users import router as users_router

__all__ = [
    "attempts_router",
    "auth_router",
    "chats_router",
    "curriculum_router",
    "documents_router",
    "flashcard_groups_router",
    "mind_maps_router",
    "notes_router",
    "papers_router",
    "practice_records_router",
    "profile_router",
    "admin_router",
    "community_router",
    "progress_router",
    "sessions_router",
    "projects_router",
    "quizzes_router",
    "review_router",
    "srq_router",
    "usage_router",
    "users_router",
]

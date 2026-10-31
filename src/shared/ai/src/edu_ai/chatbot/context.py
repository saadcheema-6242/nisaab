from typing import TYPE_CHECKING, Any

from edu_core.services.search import SearchService
from edu_queue.service import QueueService
from langchain.agents import AgentState
from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    pass


class FbiseContext(BaseModel):
    """The FBISE subject of a subject workspace, e.g. Physics XI."""

    grade_subject_id: str
    subject: str  # Physics
    grade_label: str  # Class XI (HSSC-I)
    curriculum: str | None = None  # NCP 2022-23
    has_slos: bool = False


class ChatbotContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    user_id: str
    language: str  # language code: en, ur, ur-Latn (or another code for custom projects)
    fbise: FbiseContext | None = None  # set for FBISE subject workspaces
    project_id: str
    search: "SearchService"
    queue: "QueueService"
    usage: object = (
        None  # Optional usage service (can be None or any usage service type)
    )
    llm: "BaseChatModel | None" = (
        None  # Optional LLM instance for content generation tools
    )
    # Object storage, so a generated image has somewhere to live. Without it
    # the image tool says so rather than failing.
    storage: object = None
    # What the student ticked beside the message box. None means no restriction,
    # which is what every request that does not mention tools gets.
    allowed_tools: list[str] | None = None
    web_search: bool | None = None


class ChatbotState(AgentState):
    sources: list[dict[str, Any]]

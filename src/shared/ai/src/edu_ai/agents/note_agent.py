from datetime import datetime
from typing import Any

from edu_core.exceptions import NotFoundError
from edu_db.models import Note, Project
from langchain_openai import AzureChatOpenAI
from pydantic import BaseModel, Field

from edu_ai.agents.topic_graph_agent import TopicGraphAgent
from edu_ai.agents.utils import generate, get_db_session


class NoteKeyword(BaseModel):
    """One term worth remembering, and what it means."""

    term: str = Field(..., description="The term, as it appears in the paper")
    explanation: str = Field(
        ..., description="One sentence a student could repeat in an exam"
    )


class NoteGenerationResult(BaseModel):
    """Model for note generation result."""

    title: str = Field(..., description="The title of the note")
    description: str = Field(..., description="The description of the note")
    content: str = Field(..., description="The content of the note")
    keywords: list[NoteKeyword] = Field(
        default_factory=list,
        description=(
            "The key terms from these notes, each with a one-sentence "
            "explanation. Only when keywords were asked for; otherwise empty."
        ),
    )


class NoteAgent:
    output_model = NoteGenerationResult
    prompt_template = "note_prompt"

    def __init__(
        self,
        search_service: Any,
        llm: AzureChatOpenAI,
        topic_graph_agent: TopicGraphAgent | None = None,
    ):
        self.search_service = search_service
        self.llm = llm
        self.topic_graph_agent = topic_graph_agent

    async def generate_and_save(
        self,
        project_id: str,
        topic: str | None = None,
        custom_instructions: str | None = None,
        note_id: str | None = None,
        difficulty: str | None = None,
        page_range: str | None = None,
        include_keywords: bool = False,
        **kwargs: Any,
    ) -> Note:
        """Generate note content and save to the database.

        Args:
            project_id: The project ID
            topic: Optional topic for generation
            custom_instructions: Optional custom instructions
            note_id: The note ID to populate (required)

        Returns:
            Updated Note model

        Raises:
            NotFoundError: If note or project not found
            ValueError: If note_id is not provided
        """
        if not note_id:
            raise ValueError("note_id is required for note generation")

        with get_db_session() as db:
            # Find existing note
            note = (
                db.query(Note)
                .filter(
                    Note.id == note_id,
                    Note.project_id == project_id,
                )
                .first()
            )
            if not note:
                raise NotFoundError(f"Note {note_id} not found")

            # Get project language code
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                raise NotFoundError(f"Project {project_id} not found")
            language_code = project.language_code

            generation_topic = topic
            if self.topic_graph_agent:
                topic_graph = await self.topic_graph_agent.generate_topic_graph(
                    project_id=project_id,
                    topic=topic,
                    custom_instructions=custom_instructions,
                )
                if topic_graph.root_topics:
                    topics = []
                    for root_topic in topic_graph.root_topics:
                        topics.append(root_topic.topic)
                        for subtopic in root_topic.subtopics:
                            topics.append(subtopic.topic)
                    generation_topic = ", ".join(topics)

            # Generate note using AI
            result = await generate(
                llm=self.llm,
                search_service=self.search_service,
                output_model=self.output_model,
                prompt_template=self.prompt_template,
                project_id=project_id,
                topic=generation_topic or "",
                language_code=language_code,
                custom_instructions=custom_instructions,
                difficulty=difficulty,
                page_range=page_range,
                include_keywords=include_keywords,
                subject=getattr(
                    getattr(project, "grade_subject", None), "name", ""
                )
                or "",
            )

            # Update note with generated content
            note.title = result.title
            note.description = result.description
            note.content = result.content
            if result.keywords:
                # Appended rather than stored apart: a note is one document a
                # student reads, prints and revises from, and a key-terms list
                # kept somewhere else is a list nobody opens.
                lines = "\n".join(
                    f"- **{k.term}** - {k.explanation}" for k in result.keywords
                )
                note.content = f"{result.content}\n\n## Key terms\n\n{lines}\n"
            note.updated_at = datetime.now()

            db.flush()
            return note

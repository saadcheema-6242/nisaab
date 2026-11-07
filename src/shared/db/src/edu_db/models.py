from datetime import datetime
from uuid import uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from edu_db.base import Base


class User(Base):
    __tablename__ = "users"
    # Use Supabase user ID as primary key to sync with auth.users
    id: Mapped[str] = mapped_column(
        String, primary_key=True
    )  # Maps to auth.users.id (UUID from Supabase)
    name: Mapped[str] = mapped_column(String, nullable=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Suspension. The dates are the whole state: banned_at says a ban was
    # applied, banned_until says when it lifts, and NULL there means it does
    # not. A separate "is banned" flag would eventually disagree with the
    # dates - a temporary ban expires, the flag stays true, and a student is
    # locked out for good by accident.
    banned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    banned_until: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ban_reason: Mapped[str] = mapped_column(Text, nullable=True)
    banned_by: Mapped[str] = mapped_column(String, nullable=True)

    # Relationships
    projects = relationship(
        "Project", back_populates="owner", cascade="all, delete-orphan"
    )
    documents = relationship(
        "Document", back_populates="owner", cascade="all, delete-orphan"
    )
    chats = relationship("Chat", back_populates="user", cascade="all, delete-orphan")
    usage = relationship(
        "UserUsage", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    owner_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    language_code: Mapped[str] = mapped_column(String, default="en")
    # "subject_workspace" (created by onboarding for one FBISE subject) or "custom"
    kind: Mapped[str] = mapped_column(String, default="custom", server_default="custom")
    grade_subject_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("grade_subjects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # Set when a student drops the subject by changing group. The workspace is
    # hidden rather than deleted: somebody who spent a month on Chemistry notes
    # before switching should not lose them to a dropdown, and switching back
    # brings the subject and its work with it.
    archived_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    owner = relationship("User", back_populates="projects")
    grade_subject = relationship("GradeSubject")
    documents = relationship(
        "Document", back_populates="project", cascade="all, delete-orphan"
    )
    chats = relationship("Chat", back_populates="project", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    owner_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id", ondelete="CASCADE")
    )
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=True
    )

    # File information
    file_name: Mapped[str] = mapped_column(String)  # Original file name
    file_type: Mapped[str] = mapped_column(String)  # pdf, docx, txt, etc.
    file_size: Mapped[int] = mapped_column(Integer)  # Size in bytes

    # Azure Blob Storage references
    original_blob_name: Mapped[str] = mapped_column(
        String, unique=True, nullable=True, index=True
    )
    processed_text_blob_name: Mapped[str] = mapped_column(
        String, unique=True, nullable=True, index=True
    )

    # Document metadata
    summary: Mapped[str] = mapped_column(
        Text, nullable=True
    )  # Auto-generated summary of the document

    # Document processing metadata
    status: Mapped[str] = mapped_column(String, default="uploaded")

    # Timestamps
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    owner = relationship("User", back_populates="documents")
    project = relationship("Project", back_populates="documents")
    segments = relationship(
        "DocumentSegment", back_populates="document", cascade="all, delete-orphan"
    )


class DocumentSegment(Base):
    __tablename__ = "document_segments"
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    document_id: Mapped[str] = mapped_column(
        String, ForeignKey("documents.id", ondelete="CASCADE")
    )

    # Content
    content: Mapped[str] = mapped_column(Text)
    content_type: Mapped[str] = mapped_column(String, default="text")

    # Metadata for RAG
    embedding_vector: Mapped[list] = mapped_column(Vector(3072), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    document = relationship("Document", back_populates="segments")


class Chat(Base):
    __tablename__ = "chats"
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("projects.id", ondelete="CASCADE")
    )
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id", ondelete="CASCADE")
    )
    title: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    project = relationship("Project", back_populates="chats")
    user = relationship("User", back_populates="chats")
    messages = relationship(
        "ChatMessage", back_populates="chat", cascade="all, delete-orphan"
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    chat_id: Mapped[str] = mapped_column(
        String, ForeignKey("chats.id", ondelete="CASCADE")
    )
    role: Mapped[str] = mapped_column(String)  # user, assistant
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    chat = relationship("Chat", back_populates="messages")
    parts = relationship(
        "ChatMessagePart",
        back_populates="message",
        cascade="all, delete-orphan",
        order_by="ChatMessagePart.order",
    )


class ChatMessagePart(Base):
    __tablename__ = "chat_message_parts"
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    message_id: Mapped[str] = mapped_column(
        String, ForeignKey("chat_messages.id", ondelete="CASCADE")
    )
    part_type: Mapped[str] = mapped_column(
        String
    )  # text, file, tool_call, source-document
    order: Mapped[int] = mapped_column(Integer, default=0)

    # Text part
    text_content: Mapped[str] = mapped_column(Text, nullable=True)

    # File part
    file_name: Mapped[str] = mapped_column(String, nullable=True)
    file_type: Mapped[str] = mapped_column(String, nullable=True)
    file_url: Mapped[str] = mapped_column(String, nullable=True)

    # Tool Call part
    tool_call_id: Mapped[str] = mapped_column(String, nullable=True)
    tool_name: Mapped[str] = mapped_column(String, nullable=True)
    tool_input: Mapped[dict] = mapped_column(JSON, nullable=True)
    tool_output: Mapped[dict] = mapped_column(JSON, nullable=True)
    tool_state: Mapped[str] = mapped_column(String, nullable=True)

    # Source Document part
    source_id: Mapped[str] = mapped_column(String, nullable=True)
    media_type: Mapped[str] = mapped_column(String, nullable=True)
    source_title: Mapped[str] = mapped_column(String, nullable=True)
    source_filename: Mapped[str] = mapped_column(String, nullable=True)
    provider_metadata: Mapped[dict] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    message = relationship("ChatMessage", back_populates="parts")


class FlashcardGroup(Base):
    __tablename__ = "flashcard_groups"
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("projects.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    # FBISE SLO this set practises, e.g. P-11-B-05
    slo_code: Mapped[str] = mapped_column(String, nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    project = relationship("Project")
    flashcards = relationship(
        "Flashcard", back_populates="group", cascade="all, delete-orphan"
    )


class Flashcard(Base):
    __tablename__ = "flashcards"
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    group_id: Mapped[str] = mapped_column(
        String, ForeignKey("flashcard_groups.id", ondelete="CASCADE")
    )
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("projects.id", ondelete="CASCADE")
    )

    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    difficulty_level: Mapped[str] = mapped_column(
        String, default="medium"
    )  # easy, medium, hard
    position: Mapped[int] = mapped_column(
        Integer, default=0, index=True
    )  # Position for ordering within group
    # FBISE SLO this item practises, e.g. P-11-B-05
    slo_code: Mapped[str] = mapped_column(String, nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    group = relationship("FlashcardGroup", back_populates="flashcards")
    project = relationship("Project")


class Quiz(Base):
    __tablename__ = "quizzes"
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("projects.id", ondelete="CASCADE")
    )

    name: Mapped[str] = mapped_column(String, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    # FBISE SLO this set practises, e.g. P-11-B-05
    slo_code: Mapped[str] = mapped_column(String, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    project = relationship("Project")
    questions = relationship(
        "QuizQuestion", back_populates="quiz", cascade="all, delete-orphan"
    )


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    quiz_id: Mapped[str] = mapped_column(
        String, ForeignKey("quizzes.id", ondelete="CASCADE")
    )
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("projects.id", ondelete="CASCADE")
    )

    question_text: Mapped[str] = mapped_column(Text)
    option_a: Mapped[str] = mapped_column(Text)
    option_b: Mapped[str] = mapped_column(Text)
    option_c: Mapped[str] = mapped_column(Text)
    option_d: Mapped[str] = mapped_column(Text)
    correct_option: Mapped[str] = mapped_column(String)  # a, b, c, d
    explanation: Mapped[str] = mapped_column(Text, nullable=True)
    # A diagram some questions need, drawn from a spec and kept in object
    # storage. The path, not a URL: the URL is signed when it is needed.
    image_path: Mapped[str] = mapped_column(String, nullable=True)
    image_alt: Mapped[str] = mapped_column(Text, nullable=True)
    # Pictures for the options themselves - "which of these is benzene?" - as
    # {"a": {"path": ..., "alt": ...}}. A dict rather than four columns so an
    # option without a picture simply is not there.
    option_images: Mapped[dict] = mapped_column(JSON, nullable=True)
    # Who the picture belongs to, when it came from an openly licensed source:
    # author, licence, licence_url, source_url, source. Naming them is a
    # condition of the licence, so it travels with the picture everywhere.
    image_credit: Mapped[dict] = mapped_column(JSON, nullable=True)
    difficulty_level: Mapped[str] = mapped_column(
        String, default="medium"
    )  # easy, medium, hard
    position: Mapped[int] = mapped_column(
        Integer, default=0, index=True
    )  # Position for ordering within quiz
    # FBISE SLO this item practises, e.g. P-11-B-05
    slo_code: Mapped[str] = mapped_column(String, nullable=True, index=True)
    cognitive_level: Mapped[str] = mapped_column(String, nullable=True)  # K, U or A

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    quiz = relationship("Quiz", back_populates="questions")
    project = relationship("Project")


class Note(Base):
    __tablename__ = "notes"
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("projects.id", ondelete="CASCADE")
    )
    title: Mapped[str] = mapped_column(String, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(Text)  # Markdown content

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    project = relationship("Project")


class PracticeRecord(Base):
    __tablename__ = "practice_records"
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )

    item_type: Mapped[str] = mapped_column(
        String, index=True
    )  # "flashcard" or "quiz" - type of study resource
    item_id: Mapped[str] = mapped_column(
        String, index=True
    )  # flashcard_id or quiz_question_id - ID of the study resource
    topic: Mapped[str] = mapped_column(Text)  # Extracted from question/flashcard text
    # FBISE SLO this item practises, e.g. P-11-B-05
    slo_code: Mapped[str] = mapped_column(String, nullable=True, index=True)
    user_answer: Mapped[str] = mapped_column(
        String, nullable=True
    )  # Only for quizzes, what user selected; null for flashcards
    correct_answer: Mapped[str] = mapped_column(
        Text
    )  # The correct answer - for flashcards this is the answer field, for quizzes the correct option
    was_correct: Mapped[bool] = mapped_column(
        Boolean, default=False
    )  # Whether the user got it right
    # Share of marks for written answers (0..1); null for right/wrong items
    score: Mapped[float] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    user = relationship("User")
    project = relationship("Project")


class MindMap(Base):
    __tablename__ = "mind_maps"
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )

    # Map content
    title: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    map_data: Mapped[dict] = mapped_column(
        JSON
    )  # Structured mind map data (nodes, edges)

    # Timestamps
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user = relationship("User")
    project = relationship("Project")


class FlashcardProgress(Base):
    __tablename__ = "flashcard_progress"
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    flashcard_id: Mapped[str] = mapped_column(
        String, ForeignKey("flashcards.id", ondelete="CASCADE"), index=True
    )
    group_id: Mapped[str] = mapped_column(
        String, ForeignKey("flashcard_groups.id", ondelete="CASCADE"), index=True
    )
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )

    # Simple mastery tracking
    correct_count: Mapped[int] = mapped_column(Integer, default=0)
    incorrect_count: Mapped[int] = mapped_column(Integer, default=0)
    current_streak: Mapped[int] = mapped_column(Integer, default=0)
    mastery_level: Mapped[int] = mapped_column(
        Integer, default=0
    )  # 0=unseen, 1=learning, 2=mastered
    is_mastered: Mapped[bool] = mapped_column(Boolean, default=False)
    last_result: Mapped[bool] = mapped_column(Boolean, nullable=True)
    last_practiced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user = relationship("User")
    flashcard = relationship("Flashcard")
    group = relationship("FlashcardGroup")
    project = relationship("Project")





class UserUsage(Base):
    __tablename__ = "user_usage"
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id", ondelete="CASCADE"), index=True, unique=True
    )

    # Daily usage counters (reset daily)
    chat_messages_today: Mapped[int] = mapped_column(Integer, default=0)
    flashcard_generations_today: Mapped[int] = mapped_column(Integer, default=0)
    quiz_generations_today: Mapped[int] = mapped_column(Integer, default=0)
    mindmap_generations_today: Mapped[int] = mapped_column(Integer, default=0)
    document_uploads_today: Mapped[int] = mapped_column(Integer, default=0)
    # Posting had no cap at all, which mattered more than it looks: nobody
    # but the author could delete a post, so an unlimited poster could fill
    # a room with things that could not be taken down.
    community_posts_today: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    # Last reset date
    last_reset_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user = relationship("User")


class Job(Base):
    """Background job for the worker (replaces the Azure Storage Queue)."""

    __tablename__ = "jobs"
    __table_args__ = (Index("ix_jobs_status_run_after", "status", "run_after"),)

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    type: Mapped[str] = mapped_column(String, index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(
        String, default="queued"
    )  # queued, running, done, failed
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    run_after: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    locked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class StudyPlan(Base):
    __tablename__ = "study_plans"
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )

    content: Mapped[dict] = mapped_column(JSON)  # Structured JSON study plan
    weak_topics: Mapped[list[str]] = mapped_column(
        JSON, default=list
    )  # List of weak topics identified

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    user = relationship("User")
    project = relationship("Project")


class Subject(Base):
    """An FSc subject, e.g. PHY Physics."""

    __tablename__ = "subjects"
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    code: Mapped[str] = mapped_column(String, unique=True)  # PHY, CHEM, BIO, MATH
    name: Mapped[str] = mapped_column(String)
    has_practical: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    grade_subjects = relationship("GradeSubject", back_populates="subject")


class GradeSubject(Base):
    """A subject in one grade under one scheme of studies, e.g. Physics XI (ISS-2024)."""

    __tablename__ = "grade_subjects"
    __table_args__ = (UniqueConstraint("subject_id", "grade", "scheme"),)

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    subject_id: Mapped[str] = mapped_column(
        String, ForeignKey("subjects.id", ondelete="CASCADE"), index=True
    )
    grade: Mapped[int] = mapped_column(Integer)  # 11 or 12
    scheme: Mapped[str] = mapped_column(String)  # ISS-2024
    curriculum: Mapped[str] = mapped_column(String, nullable=True)  # NCP 2022-23
    source_url: Mapped[str] = mapped_column(Text, nullable=True)  # FBISE AF PDF
    # "available" once the SLOs are seeded, otherwise "coming_soon"
    status: Mapped[str] = mapped_column(String, default="coming_soon")

    subject = relationship("Subject", back_populates="grade_subjects")
    domains = relationship(
        "CurriculumDomain",
        back_populates="grade_subject",
        cascade="all, delete-orphan",
        order_by="CurriculumDomain.sort_order",
    )


class CurriculumDomain(Base):
    """A domain of the FBISE SLO table, e.g. B Mechanics."""

    __tablename__ = "curriculum_domains"
    __table_args__ = (UniqueConstraint("grade_subject_id", "code"),)

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    grade_subject_id: Mapped[str] = mapped_column(
        String, ForeignKey("grade_subjects.id", ondelete="CASCADE"), index=True
    )
    code: Mapped[str] = mapped_column(String)  # A..N
    name: Mapped[str] = mapped_column(String)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    grade_subject = relationship("GradeSubject", back_populates="domains")
    slos = relationship(
        "Slo",
        back_populates="domain",
        cascade="all, delete-orphan",
        order_by="Slo.sort_order",
    )


class Slo(Base):
    """A Student Learning Outcome from the FBISE Assessment Framework."""

    __tablename__ = "slos"
    __table_args__ = (UniqueConstraint("grade_subject_id", "code"),)

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    grade_subject_id: Mapped[str] = mapped_column(
        String, ForeignKey("grade_subjects.id", ondelete="CASCADE"), index=True
    )
    domain_id: Mapped[str] = mapped_column(
        String, ForeignKey("curriculum_domains.id", ondelete="CASCADE"), index=True
    )
    code: Mapped[str] = mapped_column(String, index=True)  # P-11-B-05
    content_area: Mapped[str] = mapped_column(String, nullable=True)
    description: Mapped[str] = mapped_column(Text)
    # summative (examined), formative (classroom only) or practical (PBA)
    assessment_form: Mapped[str] = mapped_column(String)
    cognitive_levels: Mapped[list[str]] = mapped_column(JSON, default=list)  # K, U, A
    periods: Mapped[int] = mapped_column(Integer, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    domain = relationship("CurriculumDomain", back_populates="slos")


class StudentProfile(Base):
    """The student's FSc details, filled in by onboarding."""

    __tablename__ = "student_profiles"
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    grade: Mapped[int] = mapped_column(Integer)  # 11 or 12
    group_code: Mapped[str] = mapped_column(String)  # PRE_MED, PRE_ENG or ICS
    explanation_language: Mapped[str] = mapped_column(String, default="en")
    exam_year: Mapped[int] = mapped_column(Integer, nullable=True)
    onboarding_completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user = relationship("User")


class SrqQuestion(Base):
    """A short-response question (SRQ) for one SLO, with its marking rubric."""

    __tablename__ = "srq_questions"
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    slo_code: Mapped[str] = mapped_column(String, nullable=True, index=True)
    question: Mapped[str] = mapped_column(Text)  # Markdown with LaTeX
    marks: Mapped[int] = mapped_column(Integer)
    model_answer: Mapped[str] = mapped_column(Text)
    # [{"point": "...", "marks": 1}, ...]; the marks add up to `marks`
    rubric: Mapped[list[dict]] = mapped_column(JSON, default=list)
    cognitive_level: Mapped[str] = mapped_column(String, nullable=True)  # K, U or A
    source: Mapped[str] = mapped_column(String, default="ai_generated")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    attempts = relationship(
        "SrqAttempt", back_populates="question", cascade="all, delete-orphan"
    )


class SrqAttempt(Base):
    """A student's written answer to an SRQ and its AI-estimated marks."""

    __tablename__ = "srq_attempts"
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    question_id: Mapped[str] = mapped_column(
        String, ForeignKey("srq_questions.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    answer: Mapped[str] = mapped_column(Text)
    awarded_marks: Mapped[float] = mapped_column(Float)
    max_marks: Mapped[int] = mapped_column(Integer)
    # {"points": [{"point", "marks", "awarded", "comment"}], "feedback": "...", "missing": [...]}
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    question = relationship("SrqQuestion", back_populates="attempts")


class ContentItem(Base):
    """Shared, reviewable content for one SLO: an explainer, an MCQ or an SRQ.

    Generated ahead of time (scripts/content/generate_bank.py) and checked by a
    subject teacher, so practice can start instantly with reviewed material.
    """

    __tablename__ = "content_items"
    __table_args__ = (Index("ix_content_items_slo", "grade_subject_id", "slo_code", "kind"),)

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    grade_subject_id: Mapped[str] = mapped_column(
        String, ForeignKey("grade_subjects.id", ondelete="CASCADE")
    )
    slo_code: Mapped[str] = mapped_column(String)
    kind: Mapped[str] = mapped_column(String)  # explainer, mcq, srq
    # explainer: {title, content}; mcq: quiz question fields; srq: {question, marks, model_answer, rubric}
    payload: Mapped[dict] = mapped_column(JSON)
    review_status: Mapped[str] = mapped_column(
        String, default="draft", index=True
    )  # draft, approved, rejected
    review_note: Mapped[str] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[str] = mapped_column(String, nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    source: Mapped[str] = mapped_column(String, default="ai_generated")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class PracticeAttempt(Base):
    """One finished attempt at a quiz, flashcard set or practice paper.

    Keeps the score and answers so a chat card or results page can show them
    again later; the individual answers also go to practice_records for mastery.
    """

    __tablename__ = "practice_attempts"
    __table_args__ = (Index("ix_practice_attempts_ref", "user_id", "kind", "ref_id"),)

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id", ondelete="CASCADE")
    )
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String)  # quiz, flashcards, paper
    ref_id: Mapped[str] = mapped_column(String)  # quiz, flashcard group or paper ID
    # quiz: [{"question_id", "chosen", "correct_option", "is_correct"}]
    answers: Mapped[list[dict]] = mapped_column(JSON, default=list)
    score: Mapped[float] = mapped_column(Float)
    max_score: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class PracticePaper(Base):
    """A practice paper in FBISE style: MCQs, short questions (SRQ) and long questions (ERQ).

    sections: [{"id": "A", "title", "items": [{"id", "type": "mcq"|"srq"|"erq", "marks",
    "slo_code", ...}]}]. MCQ items carry the question inline; SRQ/ERQ items point to
    srq_questions rows so they are marked like any written answer.
    """

    __tablename__ = "practice_papers"
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String)
    length: Mapped[str] = mapped_column(String)  # mini, standard
    time_limit_minutes: Mapped[int] = mapped_column(Integer)
    sections: Mapped[list[dict]] = mapped_column(JSON)
    total_marks: Mapped[float] = mapped_column(Float)
    answers: Mapped[dict] = mapped_column(JSON, default=dict)  # saved as the student types
    status: Mapped[str] = mapped_column(String, default="ready")  # ready, submitted
    result: Mapped[dict] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)


class CommunityPost(Base):
    """One message in the room a student shares with their own class.

    A room is a grade and a group together - Pre-Medical XI is not the same
    room as Pre-Engineering XI - because that pair is what decides which
    papers a student sits. Both are copied onto the post rather than read from
    the author's profile when it is shown: a student who moves up to XII, or
    switches group, should not drag last year's messages into the new room or
    rewrite the old one.
    """

    __tablename__ = "community_posts"
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    grade: Mapped[int] = mapped_column(Integer, index=True)  # 11 or 12
    group_code: Mapped[str] = mapped_column(String, index=True)  # PRE_MED, PRE_ENG, ICS
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    body: Mapped[str] = mapped_column(Text)
    # A reply sits under another post. One level only: a thread a student can
    # follow, rather than a tree nobody reads to the bottom of.
    parent_id: Mapped[str] = mapped_column(
        String, ForeignKey("community_posts.id", ondelete="CASCADE"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    # What the model made of this post, written once when it is created.
    # Stored on the post rather than in a separate table because every post
    # has exactly one review and the administrator's list sorts by it: a
    # join would be a join on every row of every page.
    #
    # Null means not reviewed - the model was unreachable, or the post
    # predates review. Not the same as clean, and the admin list says so,
    # because treating "never looked at" as "looked at and fine" is how
    # something sits unnoticed for a month.
    review_finding: Mapped[str] = mapped_column(String, nullable=True, index=True)
    review_confidence: Mapped[float] = mapped_column(Float, nullable=True)
    review_why: Mapped[str] = mapped_column(Text, nullable=True)
    review_severity: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0", index=True
    )
    # Set when an administrator has looked and decided to leave it. Keeps a
    # judged post out of the queue without deleting the finding.
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reviewed_by: Mapped[str] = mapped_column(String, nullable=True)

    # Set when the author was told. A student is warned once per post, not
    # once per time somebody opens the page.
    warned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    warning_text: Mapped[str] = mapped_column(Text, nullable=True)
    # Whether the author has seen the warning yet.
    warning_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # A poll is a post with options, not a separate kind of thing, so it
    # threads and moderates like everything else.
    poll_question: Mapped[str] = mapped_column(Text, nullable=True)

    user = relationship("User")
    attachments = relationship(
        "CommunityAttachment",
        back_populates="post",
        cascade="all, delete-orphan",
        order_by="CommunityAttachment.position",
    )
    poll_options = relationship(
        "CommunityPollOption",
        back_populates="post",
        cascade="all, delete-orphan",
        order_by="CommunityPollOption.position",
    )
    reports = relationship(
        "CommunityReport", back_populates="post", cascade="all, delete-orphan"
    )


class CommunityAttachment(Base):
    """A photo, voice note or file hanging off a post.

    The bytes live in the bucket; this is the record of what and where. The
    filename is kept as the student saw it so a download arrives with a name
    they recognise, and the size so the page can say how big something is
    before anyone on a slow connection commits to it.
    """

    __tablename__ = "community_attachments"
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    post_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("community_posts.id", ondelete="CASCADE"),
        index=True,
    )
    # image, audio or file: decides how the page shows it
    kind: Mapped[str] = mapped_column(String)
    filename: Mapped[str] = mapped_column(String)
    content_type: Mapped[str] = mapped_column(String)
    size_bytes: Mapped[int] = mapped_column(Integer)
    storage_path: Mapped[str] = mapped_column(String)
    # How long a voice note runs, so the player can say so before it loads
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    post = relationship("CommunityPost", back_populates="attachments")


class CommunityPollOption(Base):
    """One answer a student can pick in a poll."""

    __tablename__ = "community_poll_options"
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    post_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("community_posts.id", ondelete="CASCADE"),
        index=True,
    )
    text: Mapped[str] = mapped_column(String)
    position: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    post = relationship("CommunityPost", back_populates="poll_options")
    votes = relationship(
        "CommunityPollVote", back_populates="option", cascade="all, delete-orphan"
    )


class CommunityPollVote(Base):
    """One student's answer to one poll.

    The unique constraint is on the poll and the student, not the option, so
    the database itself enforces one vote each. Doing it in code would mean
    two quick taps could register twice, and a poll that can be stuffed is
    not a poll.
    """

    __tablename__ = "community_poll_votes"
    __table_args__ = (
        UniqueConstraint("post_id", "user_id", name="uq_community_poll_one_vote"),
    )

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    post_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("community_posts.id", ondelete="CASCADE"),
        index=True,
    )
    option_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("community_poll_options.id", ondelete="CASCADE"),
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    option = relationship("CommunityPollOption", back_populates="votes")


class CommunityReport(Base):
    """A student saying a post needs looking at.

    One report per student per post, enforced by the database, so a group
    cannot be brigaded into looking urgent by one person tapping repeatedly.
    The count still matters: five students reporting the same post is a
    stronger signal than the model's opinion.
    """

    __tablename__ = "community_reports"
    __table_args__ = (
        UniqueConstraint("post_id", "user_id", name="uq_community_report_once"),
    )

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    post_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("community_posts.id", ondelete="CASCADE"),
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    reason: Mapped[str] = mapped_column(String, nullable=True)
    note: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    post = relationship("CommunityPost", back_populates="reports")

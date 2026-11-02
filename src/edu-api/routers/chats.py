"""Router for chat CRUD operations."""


import base64
import binascii
from collections.abc import AsyncGenerator
from uuid import uuid4

from auth import get_current_user
from dependencies import (
    get_chat_service,
    get_document_upload_service,
    get_queue_service,
    get_usage_service,
)
from edu_core.exceptions import NotFoundError
from edu_core.schemas.chats import (
    ChatDetailDto,
    ChatDto,
)
from edu_core.schemas.users import UserDto
from edu_core.storage import chat_upload_path
from edu_core.services import ChatService, UsageService
from edu_core.services.document_upload import DocumentUploadService
from edu_queue.schemas import DocumentProcessingData, QueueTaskMessage, TaskType
from edu_queue.service import QueueService
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from routers.schemas import ChatCompletionRequest, ChatCreate, ChatUpdate, FilePart

router = APIRouter(prefix="/api/v1/projects/{project_id}/chats", tags=["chats"])


@router.post("", response_model=ChatDto, status_code=201)
async def create_chat(
    project_id: str,
    chat: ChatCreate,
    current_user: UserDto = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    """Create a new chat."""
    try:
        return service.create_chat(
            project_id=project_id,
            user_id=current_user.id,
            title=chat.title,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{chat_id}", response_model=ChatDetailDto)
async def get_chat(
    project_id: str,
    chat_id: str,
    current_user: UserDto = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    """Get a chat by ID with messages and parts."""
    try:
        return service.get_chat(
            chat_id=chat_id, user_id=current_user.id, include_messages=True
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=list[ChatDto])
async def list_chats(
    project_id: str,
    current_user: UserDto = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    """List all chats for a project."""
    try:
        return service.list_chats(project_id=project_id, user_id=current_user.id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{chat_id}", response_model=ChatDto)
async def update_chat(
    project_id: str,
    chat_id: str,
    chat: ChatUpdate,
    current_user: UserDto = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    """Update a chat."""
    try:
        return service.update_chat(
            chat_id=chat_id,
            user_id=current_user.id,
            title=chat.title,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{chat_id}", status_code=204)
async def delete_chat(
    project_id: str,
    chat_id: str,
    current_user: UserDto = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    """Delete a chat."""
    try:
        service.delete_chat(chat_id=chat_id, user_id=current_user.id)
        return None
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



def _decode(part: FilePart, allowed: set[str]) -> tuple[str, str, bytes]:
    """The name, extension and bytes of one attached file, or a 400."""
    name = (part.filename or "attachment").strip()
    suffix = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if suffix not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot read '{name}'. Supported: {', '.join(sorted(allowed))}.",
        )

    encoded = part.url.split(",", 1)[-1] if "," in part.url else part.url
    try:
        content = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as error:
        raise HTTPException(
            status_code=400, detail=f"Could not read '{name}': {error}"
        ) from error
    if not content:
        raise HTTPException(status_code=400, detail=f"'{name}' is empty")
    return name, suffix, content


def _store_attachments(
    parts: list,
    project_id: str,
    user_id: str,
    upload_service: DocumentUploadService,
    queue_service: QueueService,
) -> tuple[list[dict], list[str]]:
    """Store what the student attached, each kind the way it is actually useful.

    A picture and a textbook chapter are not the same thing, and treating them
    alike is what made the tutor answer about the wrong image: the picture was
    thrown away, the tutor was told to go and search instead, and the search
    returned the nearest unrelated file.

    So:

    - A picture is kept with the conversation and handed to the tutor itself,
      which can see it. It is never indexed, so it can never be returned as a
      "source" for some later, unrelated question.
    - Anything else - a PDF, a DOCX, a text file - is too big to re-send every
      turn, so it becomes a project document and is indexed, and the tutor
      reads it with the same search it uses for everything else.

    Returns the pictures (as parts to pass to the tutor) and the filenames of
    the documents being indexed.
    """
    allowed = {t.lower() for t in upload_service.get_supported_types()}
    images: list[dict] = []
    documents: list[str] = []

    for part in parts:
        if not isinstance(part, FilePart):
            continue
        name, suffix, content = _decode(part, allowed)

        if (part.media_type or "").lower().startswith("image/"):
            path = chat_upload_path(project_id, str(uuid4()), suffix)
            upload_service.storage.upload(
                path, content, content_type=part.media_type
            )
            images.append(
                {
                    "type": "file",
                    "file_name": name,
                    "file_type": part.media_type,
                    "file_url": path,
                }
            )
            continue

        document_id = upload_service.upload_document(
            file_content=content,
            filename=name,
            project_id=project_id,
            owner_id=user_id,
        )
        queue_service.send_message(
            QueueTaskMessage(
                type=TaskType.DOCUMENT_PROCESSING,
                data=DocumentProcessingData(
                    document_id=document_id,
                    project_id=project_id,
                    user_id=user_id,
                ),
            )
        )
        documents.append(name)

    return images, documents


@router.post(
    "/{chat_id}/messages/stream",
    status_code=200,
    summary="Send a streaming message to a chat",
    description="Send a message to a chat with streaming response",
)
async def send_streaming_message(
    project_id: str,
    chat_id: str,
    body: ChatCompletionRequest,
    current_user: UserDto = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
    usage_service: UsageService = Depends(get_usage_service),
    upload_service: DocumentUploadService = Depends(get_document_upload_service),
    queue_service: QueueService = Depends(get_queue_service),
):
    """Send a streaming message to a chat."""
    user_id = current_user.id

    # Check usage limit before processing
    usage_service.check_and_increment(user_id, "chat_message")

    images, documents = _store_attachments(
        body.parts, project_id, user_id, upload_service, queue_service
    )
    for _ in documents:
        usage_service.check_and_increment(user_id, "document_upload")

    # The pictures travel with the message - the tutor can see them, so it is
    # never told to go and look for them. The base64 does not: each picture is
    # in storage now, and its path is what the message carries.
    processed_parts = [
        part.model_dump() for part in body.parts if not isinstance(part, FilePart)
    ]
    processed_parts.extend(images)

    if documents:
        # A statement of fact, not an instruction.
        #
        # This note is saved with the message and so is replayed to the tutor
        # on every later turn of the conversation. An instruction here -
        # "search the project documents to look inside" - therefore never
        # expires: three questions later, asked for a diagram, the tutor was
        # still dutifully searching and answering about the file attached
        # earlier. The tool description is where standing behaviour belongs;
        # a message should only say what happened.
        note = f"(attached: {', '.join(documents)})"
        text = next(
            (p for p in processed_parts if p.get("type") == "text"), None
        )
        if text:
            text["text"] = f"{text.get('text', '')}\n\n{note}".strip()
        else:
            processed_parts.append({"type": "text", "text": note})

    async def generate_stream() -> AsyncGenerator[bytes]:
        """Generate streaming response chunks - each part as a separate SSE event"""
        async for part_event in chat_service.stream_chat_events(
            chat_id,
            user_id,
            processed_parts,
            allowed_tools=body.tools,
            web_search=body.web_search,
        ):
            part_json = part_event.model_dump_json()
            yield f"data: {part_json}\n\n".encode("utf-8")

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
        },
    )

"""Processor for building FBISE new-pattern board papers in the background."""

from edu_core.services.papers import PaperService
from edu_queue.schemas import PaperGenerationData
from rich.console import Console

from processors.base import BaseProcessor

console = Console(force_terminal=True)


class PaperProcessor(BaseProcessor[PaperGenerationData]):
    """Builds a board paper queued by the API or the tutor."""

    async def process(self, payload: PaperGenerationData) -> None:
        await PaperService().build_board(
            paper_id=payload["paper_id"],
            project_id=payload["project_id"],
            user_id=payload["user_id"],
            length=payload["length"],
            topic=payload.get("topic"),
        )
        console.log(f"Built board paper {payload['paper_id']}")

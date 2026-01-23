import asyncio
from typing import Optional

from sse_starlette import ServerSentEvent

class Stream:
    def __init__(self) -> None:
        self._queue: Optional[asyncio.Queue[ServerSentEvent]] = None

    @property
    def queue(self) -> asyncio.Queue[ServerSentEvent]:
        if self._queue is None:
            self._queue = asyncio.Queue[ServerSentEvent]()
        return self._queue

    def __aiter__(self) -> "Stream":
        return self

    async def __anext__(self) -> ServerSentEvent:
        return await self.queue.get()

    async def asend(self, value: ServerSentEvent) -> None:
        await self.queue.put(value)

stream = Stream()

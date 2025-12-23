from __future__ import annotations

import asyncio
import os
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import status, FastAPI, Request, Response, Depends, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sse_starlette import EventSourceResponse, ServerSentEvent, JSONServerSentEvent
from pydantic import BaseModel, HttpUrl

from .clients import MCPClientError
from .container import container, lifespan

app = FastAPI(title="H.A.R.V.E.Y. Pricing Assistant API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = container.settings.harvey_static_dir
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

class ChatRequest(BaseModel):
    question: str
    pricing_url: Optional[HttpUrl] = None
    pricing_urls: Optional[List[HttpUrl]] = None
    pricing_yaml: Optional[str] = None
    pricing_yamls: Optional[List[str]] = None


class ChatResponse(BaseModel):
    answer: str
    plan: Dict[str, Any]
    result: Dict[str, Any]


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "UP"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question is required.")
    pricing_urls: List[str] = []
    if request.pricing_url:
        pricing_urls.append(str(request.pricing_url))
    if request.pricing_urls:
        pricing_urls.extend(str(url) for url in request.pricing_urls)

    pricing_yamls: List[str] = []
    if request.pricing_yaml:
        stripped = request.pricing_yaml.strip()
        if stripped:
            pricing_yamls.append(stripped)
    if request.pricing_yamls:
        pricing_yamls.extend(yaml.strip() for yaml in request.pricing_yamls if yaml and yaml.strip())

    # Deduplicate while preserving order to avoid duplicated contexts when both singular
    # and plural fields are provided or when identical contents are repeated.
    if pricing_urls:
        pricing_urls = list(dict.fromkeys(pricing_urls))
    if pricing_yamls:
        pricing_yamls = list(dict.fromkeys(pricing_yamls))

    try:
        response_payload = await container.agent.handle_question(
            question=question,
            pricing_urls=pricing_urls,
            yaml_contents=pricing_yamls,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except MCPClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - network dependent
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return ChatResponse(
        answer=response_payload["answer"],
        plan=response_payload["plan"],
        result=response_payload["result"],
    )



async def generate_events():
    i = 0
    while True:
        yield {"data": f"Event {i}"}
        i+=1
        await asyncio.sleep(2)


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

_stream = Stream()

@app.get('/events')
async def server_sent_evennts(stream: Stream = Depends(lambda: _stream)) -> EventSourceResponse:
    return EventSourceResponse(stream)

class NotificationUrlTransform(BaseModel):
    pricing_url: str
    yaml_content: str

@app.post("/transform", status_code=status.HTTP_201_CREATED)
async def url_done_update(notification: NotificationUrlTransform, stream: Stream = Depends(lambda: _stream)) -> None:
    await stream.asend(JSONServerSentEvent(event="url_transform", data={"pricing_url": notification.pricing_url, "yaml_content": notification.yaml_content}))

@app.post('/upload', status_code=status.HTTP_201_CREATED)
async def upload_and_save_pricing(file: UploadFile):
    if not (file.content_type == "application/yaml" or file.content_type == "application/x-yaml"):
        raise HTTPException(status_code=400, detail=f"Invalid Content-Type: {file.content_type}. Only application/yaml is supported")
    contents = await file.read()
    file_path = STATIC_DIR / file.filename
    with open(file_path, "wb") as pricing:
        pricing.write(contents)

    return { "filename": file.filename, "relative_path": f"/static/{file.filename}" }

@app.delete('/pricing/{filename}', status_code=204)
async def delete_pricing(filename: str):
    print(STATIC_DIR / filename)
    if (not os.path.exists(STATIC_DIR / filename)):
        raise HTTPException(status_code=404, detail=f"File with name {filename} doesn't exist")
    os.remove(STATIC_DIR / filename)
    return
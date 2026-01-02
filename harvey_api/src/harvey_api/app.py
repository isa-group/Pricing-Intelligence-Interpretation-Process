from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Annotated, Any, Dict, List, Optional

from fastapi import (
    status,
    FastAPI,
    Depends,
    UploadFile,
    HTTPException,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sse_starlette import EventSourceResponse, ServerSentEvent, JSONServerSentEvent
from pydantic import BaseModel, HttpUrl, Field

from .clients import MCPClientError
from .container import container, lifespan
from .file_manager import FileManager

app = FastAPI(title="H.A.R.V.E.Y. Pricing Assistant API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount(
    "/static",
    StaticFiles(directory=container.settings.harvey_static_dir),
    name="static",
)


class ChatUrlItem(BaseModel):
    id: str
    url: HttpUrl

class ChatRequest(BaseModel):
    question: str
    pricing_url: Optional[ChatUrlItem] = None
    pricing_urls: Optional[List[ChatUrlItem]] = None
    pricing_yaml: Optional[str] = None
    pricing_yamls: Optional[List[str]] = None


class ChatResponse(BaseModel):
    answer: str
    plan: Dict[str, Any]
    result: Dict[str, Any]

def get_file_manager():
    return FileManager(container.settings.harvey_static_dir)

@dataclass
class DbUrlItem:
    id: str
    url: str


pricing_context_db: Dict[str, ChatUrlItem] = {}
file_mangager_dependency = Annotated[FileManager, Depends(get_file_manager)]


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "UP"}


@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest, file_manager_service: file_mangager_dependency
) -> ChatResponse:
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question is required.")
    pricing_urls: List[str] = []
    if request.pricing_url:
        pricing_url_str = pydantic_url_to_str(request.pricing_url.url)
        pricing_urls.append(pricing_url_str)
        pricing_context_db[pricing_url_str] = DbUrlItem(request.pricing_url.id, pricing_url_str)
        file_manager_service.write_file(request.pricing_url.id, b"")
    if request.pricing_urls:
        pricing_urls.extend(
            str(pricing_url_item.url) for pricing_url_item in request.pricing_urls
        )
        for pricing_url_item in request.pricing_urls:
            pricing_url_str = pydantic_url_to_str(pricing_url_item.url)
            pricing_context_db[pricing_url_str] = DbUrlItem(pricing_url_item.id, pricing_url_str)
            file_manager_service.write_file(pricing_url_item.id, b"")

    pricing_yamls: List[str] = []
    if request.pricing_yaml:
        stripped = request.pricing_yaml.strip()
        if stripped:
            pricing_yamls.append(stripped)
    if request.pricing_yamls:
        pricing_yamls.extend(
            yaml.strip() for yaml in request.pricing_yamls if yaml and yaml.strip()
        )

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


@app.get("/events")
async def server_sent_evennts(
    stream: Stream = Depends(lambda: _stream),
) -> EventSourceResponse:
    return EventSourceResponse(stream)


class NotificationUrlTransform(BaseModel):
    pricing_url: HttpUrl
    yaml_content: str




@app.post("/events/url-transform", status_code=status.HTTP_201_CREATED)
async def url_done_update(
    notification: NotificationUrlTransform, stream: Stream = Depends(lambda: _stream)
) -> None:
    url_pricing_str = pydantic_url_to_str(notification.pricing_url)
    await stream.asend(
        JSONServerSentEvent(
            event="url_transform",
            data={
                "id": pricing_context_db[url_pricing_str].id,
                "pricing_url": pricing_context_db[url_pricing_str].url,
                "yaml_content": notification.yaml_content,
            },
        )
    )

def is_yaml_file(content_type: str) -> bool:
    return content_type == "application/yaml" or content_type == "application/x-yaml"


class UploadResponse(BaseModel):
    filename: str
    relative_path: str


@app.post("/upload", status_code=status.HTTP_201_CREATED, response_model=UploadResponse)
async def upload_and_save_pricing(
    file: UploadFile, file_manager_service: file_mangager_dependency
):
    if not is_yaml_file(file.content_type):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid Content-Type: {file.content_type}. Only application/yaml is supported",
        )
    contents = await file.read()
    file_manager_service.write_file(file.filename, contents)

    return UploadResponse(
        filename=file.filename, relative_path=f"/static/{file.filename}"
    )


class UploadUrlPayload(BaseModel):
    pricing_url: HttpUrl
    yaml_content: str = Field(min_length=1)


@app.post(
    "/upload/url", status_code=status.HTTP_201_CREATED, response_model=UploadResponse
)
async def upload_and_save_pricing(
    payload: UploadUrlPayload, file_manager_service: file_mangager_dependency
):
    pricing_url_str = pydantic_url_to_str(payload.pricing_url)
    if pricing_url_str not in pricing_context_db:
        raise HTTPException(
            status_code=404, detail=f"Cannot locate {pricing_url_str} in context"
        )
    filename = pricing_context_db[pricing_url_str].id
    file_manager_service.write_file(filename, payload.yaml_content.encode())
    return UploadResponse(filename=filename, relative_path=f"/static/{filename}")


@app.delete("/pricing/{filename}", status_code=204)
async def delete_pricing(filename: str, file_manager_service: file_mangager_dependency):
    try:
        file_manager_service.delete_file(filename)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"File with name {filename} doesn't exist"
        )

def pydantic_url_to_str(url: HttpUrl) -> str:
    return str(url)
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from typing import Any, AsyncIterator, Dict

from .clients import MCPWorkflowClient
from .config import get_settings
from .logging import configure_logging, get_logger
from .pricing_context import pricing_context_db
from .file_manager import FileManager

from .agent import HarveyAgent

from fastapi import FastAPI

logger = get_logger(__name__)


class ServiceContainer:
    def __init__(self) -> None:
        self._settings = get_settings()
        configure_logging(self._settings.log_level)
        self.mcp_client = MCPWorkflowClient()
        self.agent = HarveyAgent(self.mcp_client)

    @property
    def settings(self):
        return self._settings

    async def shutdown(self) -> None:
        await self.mcp_client.aclose()


container = ServiceContainer()

FILES_TTL = timedelta(days=1)
FILE_CHECKER_RATE_SECONDS = 3600


async def cleanup_expired_files(file_manager: FileManager) -> None:
    while True:
        try:
            now = datetime.now(timezone.utc)

            for key, value in list(pricing_context_db.items()):
                if now - value.created_at >= FILES_TTL:
                    logger.info("Deleting expired file %s", value.id)
                    try:
                        file_manager.delete_file(f"{value.id}.yaml")
                    except FileNotFoundError as e:
                        logger.error(e)
                    del pricing_context_db[key]
            await asyncio.sleep(FILE_CHECKER_RATE_SECONDS)
        except asyncio.CancelledError:
            logger.error("File cleaner task cancelled")
            raise
        except Exception as e:
            logger.error("Cleanup task crashed, restarting loop", error=e)
            await asyncio.sleep(1)


@asynccontextmanager
async def lifespan(app: FastAPI):

    if hasattr(app, "state"):
        app.state.container = container

    file_manager = FileManager(container.settings.harvey_static_dir)
    logger.info("File cleaner started!")
    cleanup_task = asyncio.create_task(cleanup_expired_files(file_manager))

    yield
    cleanup_task.cancel()
    await container.shutdown()

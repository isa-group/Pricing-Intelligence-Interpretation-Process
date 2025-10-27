 # task_manager.py
import asyncio
from typing import Optional, Dict, Any

class TaskManager:
    def __init__(self):
        # in-memory store; in prod you might swap for Redis, a database, etc.
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def create_task(self, task_id: str) -> None:
        """Called when a new background task is enqueued."""
        async with self._lock:
            self._tasks[task_id] = {
                "status": "pending",
                "result": None,
                "error": None
            }

    async def set_result(self, task_id: str, result: Any) -> None:
        """Mark the task completed successfully, storing its result."""
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                raise KeyError(f"Unknown task_id: {task_id}")
            task["status"] = "completed"
            task["result"] = result

    async def set_error(self, task_id: str, error: str) -> None:
        """Mark the task as failed, storing its error message."""
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                raise KeyError(f"Unknown task_id: {task_id}")
            task["status"] = "failed"
            task["error"] = error

    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve the current status, result, and/or error of a task."""
        async with self._lock:
            return self._tasks.get(task_id)

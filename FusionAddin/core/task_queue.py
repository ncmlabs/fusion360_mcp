"""Thread-safe task queue for Fusion 360 add-in.

Provides a queue-based mechanism for passing tasks from the HTTP server
thread to Fusion's main thread via custom events.
"""

import queue
import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from datetime import datetime

# Default task timeout in seconds
DEFAULT_TIMEOUT = 30.0


@dataclass
class Task:
    """A task to be executed on the main thread."""
    name: str
    args: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class TaskResult:
    """Result of a completed task."""
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    error_type: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data: Dict[str, Any] = {"success": self.success}
        if self.success:
            if self.result is not None:
                data["data"] = self.result
        else:
            if self.error:
                data["error"] = self.error
            if self.error_type:
                data["error_type"] = self.error_type
        return data


# Module-level singletons
_task_queue: Optional[queue.Queue] = None
_task_results: Dict[str, Optional[TaskResult]] = {}
_task_events: Dict[str, threading.Event] = {}
_lock = threading.Lock()


def get_task_queue() -> queue.Queue:
    """Get the global task queue."""
    global _task_queue
    if _task_queue is None:
        _task_queue = queue.Queue()
    return _task_queue


def create_task(name: str, args: Optional[Dict[str, Any]] = None) -> Task:
    """Create a new task and register it for result tracking."""
    task = Task(name=name, args=args or {})

    with _lock:
        _task_events[task.id] = threading.Event()
        _task_results[task.id] = None

    return task


def submit_task(task: Task) -> None:
    """Submit a task to the queue for processing."""
    get_task_queue().put(task)


def set_task_result(
    task_id: str,
    success: bool,
    result: Optional[Any] = None,
    error: Optional[str] = None,
    error_type: Optional[str] = None
) -> None:
    """Set the result for a completed task."""
    with _lock:
        _task_results[task_id] = TaskResult(
            success=success,
            result=result,
            error=error,
            error_type=error_type
        )
        event = _task_events.get(task_id)
        if event:
            event.set()


def wait_for_result(task_id: str, timeout: float = DEFAULT_TIMEOUT) -> TaskResult:
    """Wait for a task result with timeout."""
    event = _task_events.get(task_id)

    if not event:
        return TaskResult(
            success=False,
            error="Task not found",
            error_type="INTERNAL_ERROR"
        )

    completed = event.wait(timeout)

    with _lock:
        result = _task_results.pop(task_id, None)
        _task_events.pop(task_id, None)

    if not completed:
        return TaskResult(
            success=False,
            error=f"Task execution timed out after {timeout}s",
            error_type="TIMEOUT"
        )

    return result or TaskResult(
        success=False,
        error="No result available",
        error_type="INTERNAL_ERROR"
    )


def execute_and_wait(
    name: str,
    args: Optional[Dict[str, Any]] = None,
    timeout: float = DEFAULT_TIMEOUT
) -> TaskResult:
    """Create, submit, and wait for a task in one call."""
    task = create_task(name, args)
    submit_task(task)
    return wait_for_result(task.id, timeout)


def clear_queue() -> int:
    """Clear all pending tasks from the queue. Returns count of cleared tasks."""
    count = 0
    q = get_task_queue()

    while not q.empty():
        try:
            q.get_nowait()
            count += 1
        except queue.Empty:
            break

    return count


def reset() -> None:
    """Reset the task system (for testing or shutdown)."""
    global _task_queue, _task_results, _task_events

    with _lock:
        clear_queue()
        _task_queue = None
        _task_results.clear()
        _task_events.clear()


def pending_count() -> int:
    """Get the number of pending tasks."""
    return get_task_queue().qsize()

"""Event management for Fusion 360 add-in.

Handles custom events for thread-safe communication between
the HTTP server thread and Fusion's main thread.

Note: This module requires the Fusion 360 API (adsk.core, adsk.fusion).
It will only work when loaded as a Fusion 360 add-in.
"""

import json
import threading
from typing import Callable, Dict, Any, Optional, List

# Type alias for event handlers
EventHandler = Callable[[Dict[str, Any]], Optional[Dict[str, Any]]]


class EventManager:
    """Manages custom events for thread-safe task execution.

    This class wraps Fusion 360's custom event system to enable
    communication between the HTTP server thread and Fusion's main thread.
    """

    def __init__(self, app: Any):
        """Initialize the event manager.

        Args:
            app: The Fusion 360 Application object (adsk.core.Application)
        """
        self.app = app
        self.ui = app.userInterface if app else None
        self._event_name = "FusionMCPTaskEvent"
        self._custom_event: Optional[Any] = None
        self._event_handler: Optional[Any] = None
        self._handlers: List[Any] = []
        self._task_handlers: Dict[str, EventHandler] = {}
        self._stop_flag: Optional[threading.Event] = None
        self._polling_thread: Optional[threading.Thread] = None
        self._is_running = False

    def register_task_handler(self, task_name: str, handler: EventHandler) -> None:
        """Register a handler for a specific task type.

        Args:
            task_name: The task name that triggers this handler
            handler: A function that takes task args and returns result
        """
        self._task_handlers[task_name] = handler

    def unregister_task_handler(self, task_name: str) -> None:
        """Unregister a task handler."""
        self._task_handlers.pop(task_name, None)

    def get_handler(self, task_name: str) -> Optional[EventHandler]:
        """Get handler for a task type."""
        return self._task_handlers.get(task_name)

    def start(self) -> bool:
        """Start the event manager and polling thread.

        Returns:
            True if started successfully, False otherwise
        """
        try:
            import adsk.core

            # Register custom event
            self._custom_event = self.app.registerCustomEvent(self._event_name)

            # Create and register event handler
            self._event_handler = _create_task_event_handler(self)
            self._custom_event.add(self._event_handler)
            self._handlers.append(self._event_handler)

            # Start polling thread
            self._stop_flag = threading.Event()
            self._polling_thread = PollingThread(
                self.app,
                self._event_name,
                self._stop_flag
            )
            self._polling_thread.daemon = True
            self._polling_thread.start()

            self._is_running = True
            return True

        except Exception as e:
            self._log_error(f"Failed to start event manager: {e}")
            return False

    def stop(self) -> None:
        """Stop the event manager and cleanup."""
        self._is_running = False

        # Stop polling thread
        if self._stop_flag:
            self._stop_flag.set()

        # Remove event handlers
        for handler in self._handlers:
            try:
                if self._custom_event:
                    self._custom_event.remove(handler)
            except:
                pass
        self._handlers.clear()

        # Unregister custom event
        try:
            if self._custom_event:
                self.app.unregisterCustomEvent(self._event_name)
        except:
            pass

        self._custom_event = None
        self._event_handler = None

    @property
    def is_running(self) -> bool:
        """Check if the event manager is running."""
        return self._is_running

    def _log_error(self, message: str) -> None:
        """Log error (visible in Fusion 360)."""
        try:
            if self.ui:
                self.ui.messageBox(f"EventManager Error: {message}")
        except:
            pass


def _create_task_event_handler(manager: "EventManager") -> Any:
    """Create a TaskEventHandler that inherits from adsk.core.CustomEventHandler.

    This function dynamically creates the handler class to properly inherit
    from the Fusion 360 API base class.

    Args:
        manager: The EventManager instance

    Returns:
        A TaskEventHandler instance
    """
    import adsk.core
    from .task_queue import get_task_queue, set_task_result

    class TaskEventHandler(adsk.core.CustomEventHandler):
        """Handles custom events for task processing."""

        def __init__(self):
            super().__init__()
            self.manager = manager
            self._get_queue = get_task_queue
            self._set_result = set_task_result

        def notify(self, args: adsk.core.CustomEventArgs) -> None:
            """Called when custom event fires - process pending tasks."""
            try:
                import queue as queue_module
                task_queue = self._get_queue()

                # Process all pending tasks
                while not task_queue.empty():
                    try:
                        task = task_queue.get_nowait()
                        self._process_task(task)
                    except queue_module.Empty:
                        break
                    except Exception as e:
                        # Log but continue processing
                        pass

            except Exception as e:
                try:
                    if self.manager.ui:
                        import traceback
                        self.manager.ui.messageBox(
                            f"Task processing error: {traceback.format_exc()}"
                        )
                except:
                    pass

        def _process_task(self, task: Any) -> None:
            """Process a single task."""
            try:
                handler = self.manager.get_handler(task.name)

                if handler is None:
                    self._set_result(
                        task.id,
                        success=False,
                        error=f"Unknown task: {task.name}",
                        error_type="UNKNOWN_TASK"
                    )
                    return

                # Execute the handler
                result = handler(task.args)
                self._set_result(task.id, success=True, result=result)

            except Exception as e:
                self._set_result(
                    task.id,
                    success=False,
                    error=str(e),
                    error_type=type(e).__name__
                )

    return TaskEventHandler()


class PollingThread(threading.Thread):
    """Thread that periodically fires custom event to process tasks."""

    def __init__(
        self,
        app: Any,
        event_name: str,
        stop_flag: threading.Event,
        interval_ms: int = 100
    ):
        super().__init__()
        self.app = app
        self.event_name = event_name
        self.stop_flag = stop_flag
        self.interval_s = interval_ms / 1000.0

    def run(self) -> None:
        """Polling loop."""
        while not self.stop_flag.wait(self.interval_s):
            try:
                self.app.fireCustomEvent(self.event_name, json.dumps({}))
            except:
                # App may be closing
                break


# For use outside of Fusion 360 (testing)
def create_mock_event_manager() -> EventManager:
    """Create a mock event manager for testing outside Fusion 360."""

    class MockApp:
        userInterface = None

        def registerCustomEvent(self, name: str) -> Any:
            class MockEvent:
                def add(self, handler: Any) -> None:
                    pass
                def remove(self, handler: Any) -> None:
                    pass
            return MockEvent()

        def unregisterCustomEvent(self, name: str) -> None:
            pass

        def fireCustomEvent(self, name: str, data: str) -> None:
            pass

    return EventManager(MockApp())

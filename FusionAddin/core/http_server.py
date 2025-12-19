"""HTTP server for Fusion 360 add-in.

Provides HTTP interface for the MCP server to communicate with Fusion 360.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
from http import HTTPStatus
import json
import threading
from typing import Any, Dict, Optional, Callable, Tuple
from dataclasses import dataclass

from .task_queue import execute_and_wait, TaskResult, DEFAULT_TIMEOUT

# Type alias for request handlers
RequestHandler = Callable[[Dict[str, Any]], Tuple[int, Dict[str, Any]]]


@dataclass
class ServerConfig:
    """HTTP server configuration."""
    host: str = "localhost"
    port: int = 5001
    request_timeout: float = DEFAULT_TIMEOUT


class FusionHTTPHandler(BaseHTTPRequestHandler):
    """HTTP request handler for Fusion MCP endpoints."""

    # Class-level route registry
    _routes: Dict[str, Dict[str, str]] = {
        "GET": {},   # path -> task_name
        "POST": {},  # path -> task_name
    }

    # Custom handlers that don't go through task queue
    _custom_handlers: Dict[str, Dict[str, RequestHandler]] = {
        "GET": {},
        "POST": {},
    }

    @classmethod
    def register_route(
        cls,
        method: str,
        path: str,
        task_name: str
    ) -> None:
        """Register a route that maps to a task.

        Args:
            method: HTTP method (GET, POST)
            path: URL path
            task_name: Name of the task to execute
        """
        cls._routes[method.upper()][path] = task_name

    @classmethod
    def register_custom_handler(
        cls,
        method: str,
        path: str,
        handler: RequestHandler
    ) -> None:
        """Register a custom handler for a route.

        Args:
            method: HTTP method (GET, POST)
            path: URL path
            handler: Function that takes request body and returns (status, response)
        """
        cls._custom_handlers[method.upper()][path] = handler

    @classmethod
    def clear_routes(cls) -> None:
        """Clear all registered routes."""
        cls._routes = {"GET": {}, "POST": {}}
        cls._custom_handlers = {"GET": {}, "POST": {}}

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress default logging."""
        pass

    def _send_json_response(
        self,
        status_code: int,
        data: Dict[str, Any]
    ) -> None:
        """Send a JSON response.

        Args:
            status_code: HTTP status code
            data: Response data to serialize as JSON
        """
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def _parse_request_body(self) -> Dict[str, Any]:
        """Parse JSON request body.

        Returns:
            Parsed JSON body as dictionary, or empty dict if no body
        """
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}

        body = self.rfile.read(content_length)
        return json.loads(body) if body else {}

    def _handle_task_route(
        self,
        task_name: str,
        args: Dict[str, Any],
    ) -> None:
        """Handle a route by submitting a task and waiting for result.

        Args:
            task_name: Name of the task to execute
            args: Task arguments from request
        """
        try:
            result = execute_and_wait(task_name, args)

            if result.success:
                response: Dict[str, Any] = {"success": True}
                if result.result is not None:
                    response["data"] = result.result
                self._send_json_response(HTTPStatus.OK, response)
            else:
                status = (
                    HTTPStatus.GATEWAY_TIMEOUT
                    if result.error_type == "TIMEOUT"
                    else HTTPStatus.INTERNAL_SERVER_ERROR
                )
                self._send_json_response(status, result.to_dict())

        except Exception as e:
            self._send_json_response(HTTPStatus.INTERNAL_SERVER_ERROR, {
                "success": False,
                "error": str(e),
                "error_type": "REQUEST_ERROR",
            })

    def do_GET(self) -> None:
        """Handle GET requests."""
        path = self.path.split("?")[0]  # Remove query string

        # Check for custom handler
        if path in self._custom_handlers["GET"]:
            try:
                handler = self._custom_handlers["GET"][path]
                status_code, response = handler({})
                self._send_json_response(status_code, response)
            except Exception as e:
                self._send_json_response(HTTPStatus.INTERNAL_SERVER_ERROR, {
                    "success": False,
                    "error": str(e),
                })
            return

        # Check for task route
        if path in self._routes["GET"]:
            task_name = self._routes["GET"][path]
            self._handle_task_route(task_name, {})
            return

        self._send_json_response(HTTPStatus.NOT_FOUND, {
            "success": False,
            "error": f"Unknown endpoint: {path}",
        })

    def do_POST(self) -> None:
        """Handle POST requests."""
        path = self.path.split("?")[0]

        try:
            body = self._parse_request_body()
        except json.JSONDecodeError as e:
            self._send_json_response(HTTPStatus.BAD_REQUEST, {
                "success": False,
                "error": f"Invalid JSON: {e}",
            })
            return

        # Check for custom handler
        if path in self._custom_handlers["POST"]:
            try:
                handler = self._custom_handlers["POST"][path]
                status_code, response = handler(body)
                self._send_json_response(status_code, response)
            except Exception as e:
                self._send_json_response(HTTPStatus.INTERNAL_SERVER_ERROR, {
                    "success": False,
                    "error": str(e),
                })
            return

        # Check for task route
        if path in self._routes["POST"]:
            task_name = self._routes["POST"][path]
            self._handle_task_route(task_name, body)
            return

        self._send_json_response(HTTPStatus.NOT_FOUND, {
            "success": False,
            "error": f"Unknown endpoint: {path}",
        })

    def do_OPTIONS(self) -> None:
        """Handle CORS preflight requests."""
        self.send_response(HTTPStatus.OK)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


class FusionHTTPServer:
    """HTTP server manager for Fusion add-in."""

    def __init__(self, config: Optional[ServerConfig] = None):
        """Initialize the HTTP server.

        Args:
            config: Server configuration, or None for defaults
        """
        self.config = config or ServerConfig()
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._is_running = False

    def start(self) -> bool:
        """Start the HTTP server in a background thread.

        Returns:
            True if started successfully, False otherwise
        """
        try:
            self._server = HTTPServer(
                (self.config.host, self.config.port),
                FusionHTTPHandler
            )

            self._thread = threading.Thread(target=self._serve)
            self._thread.daemon = True
            self._thread.start()

            self._is_running = True
            return True

        except Exception as e:
            return False

    def _serve(self) -> None:
        """Server loop (runs in thread)."""
        if self._server:
            self._server.serve_forever()

    def stop(self) -> None:
        """Stop the HTTP server."""
        self._is_running = False

        if self._server:
            try:
                self._server.shutdown()
                self._server.server_close()
            except:
                pass

        self._server = None
        self._thread = None

    @property
    def is_running(self) -> bool:
        """Check if the server is running."""
        return self._is_running

    @property
    def address(self) -> str:
        """Get the server address."""
        return f"http://{self.config.host}:{self.config.port}"


# Add-in version info
ADDIN_VERSION = "0.1.0"
ADDIN_NAME = "FusionMCP"


# Default health check handler
def health_check_handler(args: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    """Health check endpoint handler.

    Returns:
        Tuple of (status_code, response_dict)
    """
    return HTTPStatus.OK, {
        "success": True,
        "message": "Fusion 360 MCP Add-in is running",
        "status": "healthy",
        "version": ADDIN_VERSION,
    }


def version_handler(args: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    """Version endpoint handler.

    Returns:
        Tuple of (status_code, response_dict)
    """
    import adsk.core
    app = adsk.core.Application.get()
    return HTTPStatus.OK, {
        "success": True,
        "addin_name": ADDIN_NAME,
        "addin_version": ADDIN_VERSION,
        "fusion_version": app.version if app else "unknown",
        "api_version": "1.0",
    }


def setup_default_routes() -> None:
    """Setup default routes for the HTTP server."""
    FusionHTTPHandler.register_custom_handler("GET", "/health", health_check_handler)
    FusionHTTPHandler.register_custom_handler("GET", "/version", version_handler)
    FusionHTTPHandler.register_custom_handler("GET", "/test", health_check_handler)

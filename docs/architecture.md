# Fusion 360 MCP Server Architecture

## Overview

The Fusion 360 MCP Server enables AI assistants to interact with Autodesk Fusion 360 for CAD design through the Model Context Protocol (MCP). The system consists of two main components that communicate over HTTP.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AI Assistant (e.g., Claude)                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       │ MCP Protocol (SSE/stdio)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MCP Server (Python)                                │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                         FastMCP Server                               │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │    │
│  │  │  Query   │ │ Creation │ │ Modify   │ │ Validate │ │ System   │  │    │
│  │  │  Tools   │ │  Tools   │ │  Tools   │ │  Tools   │ │  Tools   │  │    │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                       │                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                       FusionClient (httpx)                          │    │
│  │  • Async HTTP client        • Retry logic with backoff              │    │
│  │  • Connection pooling       • Error response handling               │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       │ HTTP (localhost:5001)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Fusion 360 Add-in (Python)                           │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                       HTTP Server                                    │    │
│  │  • Route registration       • JSON request/response                 │    │
│  │  • CORS headers             • Error handling                        │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                       │                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                       Task Queue                                     │    │
│  │  • Thread-safe execution    • 30s timeout                           │    │
│  │  • Main thread marshalling  • Result handling                       │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                       │                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                      Event Manager                                   │    │
│  │  • Custom event handling    • Fusion API integration                │    │
│  │  • Polling thread           • Thread-safe comms                     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                       │                                      │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                         Operations Layer                              │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐    │  │
│  │  │  Body    │ │ Sketch   │ │ Feature  │ │ Modify   │ │ Validate │    │  │
│  │  │   Ops    │ │   Ops    │ │   Ops    │ │   Ops    │ │   Ops    │    │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘    │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                       │                                      │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                        Entity Registry                                │  │
│  │  • Stable ID tracking       • Name-to-entity mapping                 │  │
│  │  • Cross-query persistence  • Collision prevention                   │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       │ Fusion 360 API (adsk.core, adsk.fusion)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Autodesk Fusion 360                                │
│                         (CAD Application)                                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Component Details

### MCP Server

The MCP Server is a Python application that implements the Model Context Protocol to expose Fusion 360 functionality as tools.

**Location:** `Server/src/fusion360_mcp_server/`

#### Key Files

| File | Purpose |
|------|---------|
| `main.py` | Entry point, FastMCP setup, tool registration |
| `config.py` | Configuration management via pydantic-settings |
| `logging.py` | Structured logging with correlation IDs |
| `services/fusion_client.py` | Async HTTP client for add-in communication |
| `tools/*.py` | MCP tool implementations |
| `models/*.py` | Pydantic models for data validation |

#### Tool Categories

1. **Query Tools** - Read design state, bodies, sketches, parameters, timeline
2. **Creation Tools** - Create primitives, sketches, features
3. **Modification Tools** - Move, rotate, modify, delete entities
4. **Validation Tools** - Measure distances, check interference
5. **System Tools** - Health check, version info

### Fusion 360 Add-in

The add-in runs inside Fusion 360 and provides an HTTP API for the MCP Server.

**Location:** `FusionAddin/`

#### Key Files

| File | Purpose |
|------|---------|
| `FusionMCP.py` | Add-in entry point, lifecycle management |
| `core/http_server.py` | HTTP request handler |
| `core/task_queue.py` | Thread-safe task execution |
| `core/event_manager.py` | Fusion event integration |
| `core/entity_registry.py` | Stable entity ID tracking |
| `handlers/*.py` | HTTP request handlers |
| `operations/*.py` | Fusion API operations |
| `serializers/*.py` | Entity-to-JSON serialization |

### Shared Code

Code shared between Server and Add-in.

**Location:** `shared/`

| File | Purpose |
|------|---------|
| `exceptions.py` | Custom exception hierarchy |
| `api_schema.py` | API endpoint definitions |

## Data Flow

### Query Flow

```
1. AI calls MCP tool (e.g., get_bodies)
2. FastMCP dispatches to tool function
3. Tool creates FusionClient, makes HTTP request
4. Add-in HTTP server receives request
5. Task queued for main thread execution
6. Operation queries Fusion 360 API
7. Result serialized to JSON
8. Response returned to MCP Server
9. Tool returns result to AI
```

### Creation Flow

```
1. AI calls creation tool (e.g., create_box)
2. Parameters validated by Pydantic
3. HTTP POST to add-in
4. Task queued with parameters
5. Operation creates geometry in Fusion
6. Entity registered with stable ID
7. Result with IDs returned
8. AI can reference IDs in subsequent calls
```

### Modification Flow

```
1. AI calls modification tool with entity ID
2. Add-in looks up entity in registry
3. Modification applied to Fusion model
4. Design history updated
5. New state returned to AI
```

## Threading Model

### Add-in Threading

Fusion 360 requires all API calls on the main thread. The add-in uses:

1. **HTTP Thread** - Handles incoming requests
2. **Polling Thread** - Monitors event queue
3. **Main Thread** - Executes Fusion API calls

```
HTTP Request → Task Queue → Custom Event → Main Thread Execution → Response
```

### MCP Server Threading

The MCP Server uses async/await for non-blocking I/O:

```python
async with FusionClient() as client:
    result = await client.get_bodies()
```

## Error Handling

### Exception Hierarchy

```
FusionMCPError (base)
├── EntityNotFoundError      # Entity doesn't exist
├── InvalidParameterError    # Invalid input value
├── GeometryError            # Geometry operation failed
├── ConstraintError          # Sketch constraint issue
├── FeatureError             # Feature creation failed
├── SelectionError           # Wrong entity type
├── ConnectionError          # Can't connect to add-in
├── TimeoutError             # Operation timed out
└── DesignStateError         # Invalid design state
```

### Error Context

All errors include:
- Error type identifier
- Human-readable message
- Actionable suggestion
- Correlation ID for tracing
- Context-specific data

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FUSION_MCP_HOST` | localhost | Add-in host |
| `FUSION_MCP_PORT` | 5001 | Add-in port |
| `FUSION_MCP_LOG_LEVEL` | INFO | Log verbosity |
| `FUSION_MCP_LOG_FORMAT` | json | Log format |
| `FUSION_MCP_REQUEST_TIMEOUT` | 30.0 | HTTP timeout (seconds) |
| `FUSION_MCP_MAX_RETRIES` | 3 | Retry attempts |

## Logging

### Structured Logging

All logs are JSON-formatted with:
- Timestamp
- Log level
- Logger name
- Correlation ID
- Message and context

Example:
```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "info",
  "logger": "fusion360_mcp_server.tools.query_tools",
  "correlation_id": "a1b2c3d4",
  "message": "get_bodies called",
  "component_id": null
}
```

### Correlation IDs

Each request gets a unique correlation ID that:
- Traces through Server and Add-in
- Appears in all related log entries
- Helps debug multi-step operations

## Security Considerations

### Current State

- HTTP communication (localhost only)
- No authentication
- No rate limiting

### Recommendations for Production

1. Add API key authentication
2. Implement rate limiting
3. Consider HTTPS with self-signed certs
4. Add audit logging for design modifications
5. Validate all input parameters

## Performance

### Optimization Strategies

1. **Connection pooling** - FusionClient reuses connections
2. **Lazy loading** - Face/edge details only when requested
3. **Caching** - Entity registry prevents redundant lookups
4. **Async I/O** - Non-blocking HTTP requests

### Benchmarks

| Operation | Target | Notes |
|-----------|--------|-------|
| Query 100 bodies | < 1s | Summary only |
| Create 10 features | < 5s | Sequential |
| Full design state | < 2s | With timeline |

## Extensibility

### Adding New Tools

1. Create tool function in appropriate `tools/*.py`
2. Add FusionClient method in `fusion_client.py`
3. Add handler in `handlers/*.py`
4. Implement operation in `operations/*.py`
5. Add serializer if new entity type
6. Write tests

### Adding New Operations

1. Implement in `operations/*.py`
2. Register handler in `FusionMCP.py`
3. Add to FusionClient
4. Create MCP tool wrapper
5. Document in API reference

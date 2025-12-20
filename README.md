# Fusion 360 MCP Server

An MCP (Model Context Protocol) server that enables AI assistants to interact with Autodesk Fusion 360 for CAD design.

## Features

- **Query Tools** - Read design state, bodies, sketches, parameters, and timeline
- **Creation Tools** - Create primitives, sketches, and features
- **Modification Tools** - Move, rotate, modify, and delete entities
- **Validation Tools** - Measure distances, check interference, verify properties
- **System Tools** - Health check, version info

## Quick Start

### Prerequisites

- Autodesk Fusion 360 (latest version)
- Python 3.10+
- MCP-compatible AI assistant (e.g., Claude)

### Installation

1. **Install the MCP Server**

   ```bash
   cd Server
   pip install -e .
   ```

2. **Install the Fusion 360 Add-in**

   Copy the `FusionAddin` folder to your Fusion 360 add-ins directory:

   - **macOS**: `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/`
   - **Windows**: `%appdata%\Autodesk\Autodesk Fusion 360\API\AddIns\`

3. **Enable the Add-in**

   In Fusion 360: Tools > Add-ins > FusionMCP > Run

### Running the Server

```bash
fusion360-mcp --transport sse
```

Or with stdio transport:

```bash
fusion360-mcp --transport stdio
```

## Configuration

Environment variables (prefix with `FUSION_MCP_`):

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | localhost | Add-in host |
| `PORT` | 5001 | Add-in port |
| `LOG_LEVEL` | INFO | Log verbosity |
| `LOG_FORMAT` | json | Log format |
| `REQUEST_TIMEOUT` | 30.0 | HTTP timeout (seconds) |
| `MAX_RETRIES` | 3 | Retry attempts |

## Documentation

- [LLM Prompt Guide](PROMPT.md) - Quick reference for LLM tool selection and workflows
- [API Reference](docs/api-reference.md) - Complete tool documentation
- [Architecture](docs/architecture.md) - System design and data flow
- [User Guide](docs/user-guide.md) - How to use with AI assistants
- [Troubleshooting](docs/troubleshooting.md) - Common issues and solutions

## Development

### Setup

```bash
cd Server
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Testing

```bash
pytest tests/ -v --cov=fusion360_mcp_server
```

### Linting

```bash
ruff check src/
mypy src/fusion360_mcp_server/
```

## Project Structure

```
fusion360_mcp/
├── Server/                    # MCP Server (Python)
│   ├── src/fusion360_mcp_server/
│   │   ├── main.py           # Entry point
│   │   ├── config.py         # Configuration
│   │   ├── logging.py        # Structured logging
│   │   ├── models/           # Pydantic models
│   │   ├── services/         # FusionClient
│   │   └── tools/            # MCP tools
│   └── tests/                # Unit tests
│
├── FusionAddin/              # Fusion 360 Add-in
│   ├── FusionMCP.py         # Add-in entry point
│   ├── core/                # Infrastructure
│   ├── handlers/            # HTTP handlers
│   ├── operations/          # Fusion API operations
│   └── serializers/         # Entity serialization
│
├── shared/                   # Shared code
│   └── exceptions.py        # Error hierarchy
│
└── docs/                     # Documentation
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

1. Fork the repository
2. Create a feature branch from `development`
3. Write tests for new functionality
4. Submit a pull request

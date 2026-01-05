# Contributing to Fusion 360 MCP Server

Thank you for your interest in contributing! This guide will help you get started.

## Development Setup

### Prerequisites

- Python 3.10 or higher
- Autodesk Fusion 360 (for integration testing)
- Git

### Setting Up Your Environment

1. **Fork and clone the repository**

   ```bash
   git clone https://github.com/YOUR_USERNAME/fusion360_mcp.git
   cd fusion360_mcp
   ```

2. **Create a virtual environment**

   ```bash
   cd Server
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install development dependencies**

   ```bash
   pip install -e ".[dev]"
   ```

4. **Install the Fusion 360 add-in** (for integration testing)

   Copy `FusionAddin` to your Fusion 360 add-ins directory and enable it.

## Code Style

We use automated tools to maintain code quality:

### Linting with Ruff

```bash
ruff check src/
ruff format src/  # Auto-format code
```

### Type Checking with mypy

```bash
mypy src/fusion360_mcp_server/
```

Configuration is in `pyproject.toml`. Please ensure your code passes both checks before submitting.

## Testing

Run the test suite with:

```bash
pytest tests/ -v --cov=fusion360_mcp_server
```

- Write tests for new functionality
- Ensure existing tests pass
- Aim for good coverage on new code

## Commit Messages

We use [Conventional Commits](https://www.conventionalcommits.org/) for clear history and automated changelog generation:

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(tools): Add revolve tool for 3D geometry creation
fix(client): Handle timeout errors gracefully
docs: Update installation instructions for Windows
```

## Pull Request Process

1. **Create a feature branch from `development`**

   ```bash
   git checkout development
   git pull origin development
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write clear, documented code
   - Add tests for new functionality
   - Update documentation if needed

3. **Ensure quality checks pass**

   ```bash
   ruff check src/
   mypy src/fusion360_mcp_server/
   pytest tests/ -v
   ```

4. **Push and create a pull request**

   ```bash
   git push origin feature/your-feature-name
   ```

   Then create a PR targeting the `development` branch.

5. **PR Requirements**
   - Clear description of changes
   - Link to related issue (if applicable)
   - All CI checks passing
   - Code review approval

## Reporting Issues

When reporting bugs, please include:

- Fusion 360 version
- Python version
- Operating system
- Steps to reproduce
- Expected vs actual behavior
- Relevant logs or error messages

## Questions?

Feel free to open an issue for questions or discussions about potential contributions.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

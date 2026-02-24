# Contributing to ROSForge

Thank you for your interest in contributing!

## Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/Rlin1027/ROSForge.git
   cd ROSForge
   ```

2. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. Install in development mode:
   ```bash
   pip install -e ".[dev]"
   ```

4. Run tests:
   ```bash
   pytest tests/ -q
   ```

## Code Style

- We use **ruff** for linting and formatting
- We use **mypy** for type checking
- Run before submitting:
  ```bash
  ruff check src/ tests/
  ruff format src/ tests/
  mypy src/rosforge/ --ignore-missing-imports
  ```

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Write tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## Reporting Issues

- Use GitHub Issues
- Include: Python version, OS, rosforge version, steps to reproduce

## Adding a New Engine Backend

ROSForge uses a BYOM (Bring Your Own Model) architecture. To add a new AI engine:

1. Create a new directory under `src/rosforge/engine/<name>/`
2. Implement `EngineInterface` from `src/rosforge/engine/base.py`
3. Register in `src/rosforge/engine/registry.py`
4. Add tests in `tests/unit/test_engine_<name>.py`

## Adding Knowledge Base Rules

To extend the static knowledge base:

1. Edit files in `src/rosforge/knowledge/`
2. Or create custom rules via `.rosforge/custom_rules.yaml`

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.

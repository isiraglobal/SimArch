# Contributing to SimArch

Thank you for your interest in contributing to SimArch! SimArch is an open-source platform designed for autonomous AI organizations, persistent digital workforces, and decision intelligence.

## Development Workflow

1. **Fork and Clone**
   ```bash
   git clone https://github.com/<your-username>/simarch.git
   cd simarch
   ```

2. **Environment Setup**
   Ensure Python 3.10+ is installed. Install in editable mode with development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

3. **Branching Strategy**
   Create a focused feature branch for your changes:
   ```bash
   git checkout -b feat/your-feature-name
   ```

4. **Running Tests**
   Before submitting code, ensure all tests pass:
   ```bash
   pytest tests -v --cov=simarch
   ```

5. **Code Standards**
   - Follow PEP 8 style guidelines.
   - Use strict type annotations (`typing`, `pydantic`).
   - Write unit and integration tests for new features.
   - Avoid adding unnecessary heavyweight dependencies.

## Submitting Pull Requests

- Provide a concise summary of the problem and your solution.
- Link any related issues.
- Verify that no temporary files, test databases, or credentials are included.

Thank you for helping build accountable, autonomous AI organizations!

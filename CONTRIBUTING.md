# Contributing to CodeGraph

Thank you for your interest in contributing to CodeGraph! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How to Contribute](#how-to-contribute)
- [Development Setup](#development-setup)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)
- [Pull Request Process](#pull-request-process)
- [Community](#community)

---

## Code of Conduct

We are committed to providing a welcoming and inclusive environment for all contributors. Please:

- Be respectful and considerate
- Welcome newcomers and help them get started
- Focus on constructive feedback
- Respect differing viewpoints and experiences
- Accept responsibility and apologize for mistakes
- Prioritize what is best for the community

---

## Getting Started

### Areas to Contribute

- **Code**: Backend, frontend, parsers, validators
- **Documentation**: Guides, tutorials, API docs
- **Testing**: Unit tests, integration tests, test cases
- **Examples**: Real-world usage examples
- **Bug Reports**: Identify and report issues
- **Feature Requests**: Suggest new features
- **Design**: UI/UX improvements, architecture proposals

### Good First Issues

Look for issues labeled `good-first-issue` to get started:

```bash
# View good first issues
gh issue list --label "good-first-issue"
```

---

## How to Contribute

### Reporting Bugs

Before creating a bug report:

1. **Search existing issues** to avoid duplicates
2. **Update to latest version** to see if issue persists
3. **Collect information:**
   - CodeGraph version
   - Python version
   - Neo4j version
   - Operating system
   - Steps to reproduce
   - Expected vs actual behavior
   - Error messages and logs

**Create an issue** with this template:

```markdown
### Description
Brief description of the bug

### Steps to Reproduce
1. Step one
2. Step two
3. Step three

### Expected Behavior
What should happen

### Actual Behavior
What actually happens

### Environment
- CodeGraph version: x.y.z
- Python version: 3.x
- Neo4j version: 5.x
- OS: Ubuntu 22.04

### Additional Context
Logs, screenshots, etc.
```

### Suggesting Features

Feature requests are welcome! Please:

1. **Check existing issues** to avoid duplicates
2. **Describe the use case** clearly
3. **Explain the benefit** to users
4. **Consider alternatives** and trade-offs

**Template:**

```markdown
### Feature Request
Brief description

### Use Case
Why is this needed?

### Proposed Solution
How should it work?

### Alternatives Considered
Other approaches considered

### Additional Context
Any other relevant information
```

---

## Development Setup

### Prerequisites

- Python 3.8+
- Neo4j 5.0+
- Node.js 16+ (for frontend)
- Git

### Fork and Clone

```bash
# Fork the repository on GitHub
# Then clone your fork
git clone https://github.com/YOUR_USERNAME/codegraph.git
cd codegraph

# Add upstream remote
git remote add upstream https://github.com/ORIGINAL_OWNER/codegraph.git
```

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies

# Install pre-commit hooks
pre-commit install

# Run tests
pytest
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev

# Run tests
npm test
```

### Start Neo4j

```bash
docker run -d --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest
```

---

## Coding Standards

### Python Code Style

We follow **PEP 8** with some modifications:

- **Line length**: 100 characters (not 79)
- **Indentation**: 4 spaces
- **String quotes**: Double quotes preferred
- **Type hints**: Required for all functions
- **Docstrings**: Required for public functions (Google style)

**Example:**

```python
def calculate_total(items: List[Item], discount: float = 0.0) -> float:
    """
    Calculate total price with optional discount.

    Args:
        items: List of items to sum
        discount: Discount percentage (0.0 to 1.0)

    Returns:
        Total price after discount

    Raises:
        ValueError: If discount is out of range
    """
    if not 0 <= discount <= 1:
        raise ValueError("Discount must be between 0 and 1")

    subtotal = sum(item.price for item in items)
    return subtotal * (1 - discount)
```

### TypeScript Code Style

- **Line length**: 100 characters
- **Indentation**: 2 spaces
- **String quotes**: Single quotes preferred
- **Type annotations**: Required
- **Interfaces**: Prefer interfaces over types

### Code Quality Tools

**Python:**
- `black` - Code formatting
- `isort` - Import sorting
- `mypy` - Type checking
- `pylint` - Linting
- `pytest` - Testing

**TypeScript:**
- `prettier` - Code formatting
- `eslint` - Linting
- `vitest` - Testing

**Run before committing:**

```bash
# Python
black backend/
isort backend/
mypy backend/
pylint backend/

# TypeScript
npm run lint
npm run format
```

---

## Testing

### Writing Tests

**Unit Tests:**

```python
# backend/tests/test_parser.py
import pytest
from codegraph.parser import PythonParser

def test_parse_simple_function():
    """Test parsing a simple function."""
    code = """
def add(a: int, b: int) -> int:
    return a + b
"""
    parser = PythonParser()
    entities, relationships = parser.parse_string(code)

    functions = [e for e in entities.values() if e.node_type == "Function"]
    assert len(functions) == 1
    assert functions[0].name == "add"
    assert len(functions[0].parameters) == 2
```

**Integration Tests:**

```python
# backend/tests/test_integration.py
@pytest.fixture
def db():
    db = CodeGraphDB("bolt://localhost:7687", "neo4j", "password")
    db.initialize_schema()
    yield db
    db.execute_query("MATCH (n) DETACH DELETE n")
    db.close()

def test_full_workflow(db):
    """Test complete indexing and validation workflow."""
    parser = PythonParser()
    entities, relationships = parser.parse_file("examples/test.py")

    builder = GraphBuilder(db)
    builder.build_graph(entities, relationships)

    validator = ConservationValidator(db)
    report = validator.get_validation_report()

    assert report["total_violations"] == 0
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_parser.py

# Run with coverage
pytest --cov=codegraph --cov-report=html

# Run specific test
pytest tests/test_parser.py::test_parse_simple_function

# Run tests matching pattern
pytest -k "parser"
```

### Test Coverage

We aim for 80%+ test coverage. Check coverage:

```bash
pytest --cov=codegraph --cov-report=term-missing
```

---

## Documentation

### Documentation Standards

- **Clear and concise**: Avoid jargon when possible
- **Examples**: Include code examples
- **Up-to-date**: Keep docs in sync with code
- **Well-structured**: Use proper headings and sections

### Where to Add Documentation

- **Code comments**: Explain complex logic
- **Docstrings**: Document all public functions
- **README files**: Overview and quick start
- **Guides**: In `docs/guides/`
- **Tutorials**: In `docs/tutorials/`
- **Examples**: In `docs/examples/`

### Building Documentation

```bash
# Backend docs (if using Sphinx)
cd backend/docs
make html

# View at backend/docs/_build/html/index.html
```

---

## Pull Request Process

### Before Submitting

✅ **Checklist:**

- [ ] Code follows style guide
- [ ] Tests added and passing
- [ ] Documentation updated
- [ ] Commit messages follow convention
- [ ] Branch is up-to-date with main
- [ ] Pre-commit hooks pass
- [ ] No merge conflicts

### Commit Message Convention

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Test additions or changes
- `chore`: Build process or tooling changes

**Examples:**

```
feat(parser): add support for decorators

Implemented parsing of function and class decorators.
Decorators are now represented as separate nodes with
DECORATES relationships.

Closes #123
```

```
fix(validator): handle optional parameters correctly

Previously, optional parameters were counted as required,
causing false positives in signature validation.

Fixes #456
```

### Creating a Pull Request

1. **Create a branch:**

```bash
git checkout -b feature/my-feature
# or
git checkout -b fix/my-bugfix
```

2. **Make changes and commit:**

```bash
git add .
git commit -m "feat: add my feature"
```

3. **Push to your fork:**

```bash
git push origin feature/my-feature
```

4. **Create PR on GitHub:**
   - Go to your fork on GitHub
   - Click "New Pull Request"
   - Fill out the PR template
   - Link related issues

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
How has this been tested?

## Checklist
- [ ] Tests pass
- [ ] Documentation updated
- [ ] Code follows style guide
- [ ] Commits follow convention
```

### Review Process

1. **Automated checks** run (tests, linting, etc.)
2. **Maintainer review** - may request changes
3. **Address feedback** - push additional commits
4. **Approval and merge** - maintainer merges PR

---

## Community

### Communication Channels

- **GitHub Discussions**: General questions and discussions
- **GitHub Issues**: Bug reports and feature requests
- **Discord**: [Link] (if available)

### Getting Help

- Check [documentation](docs/)
- Search existing [issues](https://github.com/owner/codegraph/issues)
- Ask in [Discussions](https://github.com/owner/codegraph/discussions)

### Recognition

Contributors are recognized in:
- `CONTRIBUTORS.md` file
- Release notes
- Project README

---

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

## Questions?

If you have questions about contributing, please:

1. Check this guide
2. Search existing issues/discussions
3. Create a new discussion

Thank you for contributing to CodeGraph! 🎉

---

**Last Updated:** 2025-01-19

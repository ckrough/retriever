# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project: GoodPuppy

AI-powered Q&A system for shelter volunteers, using RAG to answer questions from policy/procedure documents.

**Architecture:** Modular monolith with clean architecture principles (see `docs/implementation-plan.md`)

**Tech Stack:**
- Python 3.12+, FastAPI, Pydantic 2.x
- LLM: OpenRouter (Claude via OpenAI-compatible API)
- Vector DB: Chroma (embedded)
- Frontend: Jinja2 + HTMX + Tailwind CSS
- Database: SQLite

## Commands

```bash
# Install dependencies (dev)
pip install -e '.[dev]'

# Run development server
uvicorn src.main:app --reload --port 8000

# Linting and formatting
ruff check src/ tests/ --fix
ruff format src/ tests/

# Type checking (strict mode required)
mypy src/ --strict

# Run tests with coverage (80% minimum)
pytest --cov=src --cov-report=term-missing --cov-fail-under=80

# Security audit
pip-audit

# All quality checks (run before PR)
ruff check src/ tests/ --fix && ruff format src/ tests/ && mypy src/ --strict && pytest --cov=src --cov-fail-under=80
```

## Project Structure

```
src/
├── main.py                 # FastAPI app entry point
├── config.py               # Settings via pydantic-settings
├── modules/                # Business modules (self-contained)
│   ├── auth/               # Authentication
│   ├── rag/                # RAG/Q&A pipeline
│   └── documents/          # Document management
├── infrastructure/         # Shared technical concerns
│   ├── llm/                # LLM provider abstraction (Protocol-based)
│   ├── vectordb/           # Vector DB abstraction
│   ├── observability/      # Sentry + structlog
│   └── safety/             # Content moderation
├── api/                    # API layer (routes, middleware, errors)
└── web/                    # Server-rendered frontend (templates)
```

## Git Workflow: GitHub Flow

**Branch from main, PR back to main.**

```
main (protected) ← feature branches via PR
```

### Branch Naming
```
feature/add-user-auth
fix/chat-input-validation
docs/update-readme
refactor/simplify-rag-pipeline
test/add-rag-coverage
chore/update-dependencies
```

### Commit Messages (Conventional Commits)
```
feat: add volunteer login functionality
fix: resolve chat timeout on slow connections
docs: add API endpoint documentation
test: add coverage for RAG retrieval
refactor: extract LLM provider interface
chore: update dependencies
```

**Format:** `<type>: <description>` (lowercase, imperative mood, no period)

## Code Standards

### Type Hints (Required)
All function signatures must have type hints, including return types.

```python
# Good
async def ask_question(question: str, user_id: UUID) -> Answer:
    ...

# Bad - missing types
async def ask_question(question, user_id):
    ...
```

### Docstrings (Google Style)
Required for public APIs and non-trivial functions.

```python
def generate_answer(question: str, context: list[str]) -> str:
    """Generate an answer using retrieved context.

    Args:
        question: The user's question.
        context: Retrieved document chunks relevant to the question.

    Returns:
        The generated answer text.

    Raises:
        LLMProviderError: If the LLM API call fails.
    """
```

### Testing
- **Coverage:** 80% minimum for new code
- **Naming:** `test_<function>_<scenario>_<expected>`
- **Categories:** `tests/unit/`, `tests/integration/`, `tests/e2e/`

```python
def test_ask_question_with_valid_input_returns_answer():
    ...

def test_ask_question_with_empty_context_returns_fallback():
    ...
```

### Error Handling
- Never bare `except:` - always specify exception types
- Chain exceptions with `from` for context
- Use custom exception hierarchy for domain errors

## PR Requirements

Before opening a PR:
- [ ] All tests pass (`pytest`)
- [ ] Types check (`mypy --strict`)
- [ ] Linting passes (`ruff check && ruff format`)
- [ ] New code has tests (80% coverage)
- [ ] Documentation updated if needed
- [ ] ADR created for significant architectural decisions

**Review process:**
- 1 approval required
- CI must pass
- Squash merge to main

## Security

**Never commit:**
- API keys, secrets, passwords
- `.env` files (use `.env.example` as template)
- Credentials of any kind

**Required:**
- Secrets in environment variables only
- Input validation on all endpoints
- Content moderation on user input (OpenAI Moderation API)

## Key Patterns

### LLM Provider Abstraction
Use Protocol-based interface for swappable LLM providers:

```python
class LLMProvider(Protocol):
    async def complete(
        self,
        system_prompt: str,
        user_message: str,
        model: str | None = None
    ) -> str: ...
```

### Module Structure
Each module in `src/modules/` is self-contained:
```
module_name/
├── __init__.py
├── routes.py       # FastAPI routes
├── services.py     # Business logic
├── schemas.py      # Pydantic models
├── models.py       # Domain models
└── repos.py        # Data access (if needed)
```

### Configuration
Use `pydantic-settings` for all configuration. Environment variables override defaults.

## Documentation

| What | Where |
|------|-------|
| Architecture & Plan | `docs/implementation-plan.md` |
| ADRs | `docs/decisions/NNN-*.md` |
| API Docs | Auto-generated at `/docs` (OpenAPI) |
| Setup | `README.md` |
| Config | `.env.example` |

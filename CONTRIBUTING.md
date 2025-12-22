# Contributing to Retriever

Thank you for your interest in contributing to Retriever! We welcome contributions of all kinds—bug fixes, new features, documentation improvements, tests, and more.

Retriever is an AI-powered question-answering system that helps users find information in organizational documents using RAG (Retrieval-Augmented Generation). Whether you're fixing a typo or implementing a new feature, your contribution helps make documentation more accessible.

**First-time contributor?** Don't worry! This guide will walk you through everything you need to know. We're here to help if you get stuck.

## Quick Start

Get up and running in 5 minutes:

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/YOUR-USERNAME/retriever.git
cd retriever

# Install dependencies (requires Python 3.13+)
uv sync --extra dev

# Copy environment template and add your API keys
cp .env.example .env
# Edit .env with your OpenRouter and OpenAI API keys

# Verify everything works
uv run pytest
```

**Note:** You'll need API keys from [OpenRouter](https://openrouter.ai/keys) and [OpenAI](https://platform.openai.com/api-keys) for full functionality. See the [README](README.md) for detailed setup instructions.

## Development Setup

### Requirements

- **Python 3.13+** — We use modern Python features
- **[uv](https://docs.astral.sh/uv/)** — Fast Python package manager (recommended over pip)
- **API Keys** — OpenRouter (for LLM) and OpenAI (for embeddings/moderation)

### Environment Configuration

1. Copy `.env.example` to `.env`
2. Add your API keys:
   ```bash
   OPENROUTER_API_KEY=your-key-here
   OPENAI_API_KEY=your-key-here
   JWT_SECRET_KEY=generate-a-random-secret
   ```

3. Run the development server:
   ```bash
   uv run uvicorn src.main:app --reload --port 8000
   ```

Visit [http://localhost:8000](http://localhost:8000) to see the app running.

### Docker Development (Optional)

If you prefer Docker for development:

```bash
# Build the image
docker build -t retriever:latest .

# Run with docker-compose
docker-compose up -d

# View logs
docker-compose logs -f retriever

# Create a user (inside container)
docker-compose exec retriever uv run python scripts/create_user.py

# Stop
docker-compose down
```

**Note:** Active development is typically done on the host with `uv run uvicorn --reload` for faster iteration. Docker is mainly for testing the production build locally.

### Understanding the Codebase

- **Quick patterns & conventions** → [CLAUDE.md](CLAUDE.md)
- **Architecture deep dive** → [docs/architecture.md](docs/architecture.md)
- **Implementation roadmap** → [docs/increments.md](docs/increments.md)
- **Deployment guide** → [docs/guides/deployment.md](docs/guides/deployment.md)

## Making Changes

We use **GitHub Flow**: feature branches → pull request → squash merge to `main`.

### Workflow

1. **Check you're on main and up to date:**
   ```bash
   git checkout main
   git pull origin main
   ```

2. **Create a feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Branch naming conventions:**
   - `feature/` — New features (e.g., `feature/add-caching`)
   - `fix/` — Bug fixes (e.g., `fix/chat-timeout`)
   - `docs/` — Documentation (e.g., `docs/update-readme`)
   - `refactor/` — Code improvements (e.g., `refactor/simplify-llm`)
   - `test/` — Tests (e.g., `test/add-rag-coverage`)
   - `chore/` — Maintenance (e.g., `chore/update-deps`)

4. **Make your changes, commit, and push:**
   ```bash
   git add .
   git commit -m "feat: add semantic caching"
   git push origin feature/your-feature-name
   ```

5. **Open a pull request** against the `main` branch on GitHub.

See [docs/development-standards.md](docs/development-standards.md) for the complete Git workflow guide.

## Code Standards

We maintain high code quality to ensure the codebase is maintainable and reliable.

### Type Hints (Required)

All functions must have type hints, including return types:

```python
# ✅ Good
async def ask_question(question: str, user_id: UUID) -> Answer:
    ...

# ❌ Bad - missing type hints
async def ask_question(question, user_id):
    ...
```

**Why?** Type hints enable IDE support, catch bugs early, and make code self-documenting.

### Docstrings (Google Style)

Required for public APIs and non-trivial functions:

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

### Error Handling

- Never use bare `except:` — always specify exception types
- Chain exceptions with `from` for context:

```python
try:
    result = await risky_operation()
except SpecificError as e:
    logger.error("Operation failed", error=str(e))
    raise DomainError("User-friendly message") from e
```

### Security

**Never commit:**
- API keys or secrets
- `.env` files (use `.env.example` as template)
- Credentials of any kind

**Always:**
- Store secrets in environment variables
- Validate user input
- Use content moderation for user-generated content

See [CLAUDE.md](CLAUDE.md) for quick reference patterns and [docs/development-standards.md](docs/development-standards.md) for comprehensive standards.

## Testing & Quality Checks

### Coverage Requirements

**80% minimum** for new code. We're pragmatic, not dogmatic—focus on testing business logic and edge cases.

### Test Naming

Use descriptive names: `test_<function>_<scenario>_<expected>`

```python
def test_ask_question_with_valid_input_returns_answer():
    ...

def test_ask_question_with_empty_context_returns_fallback():
    ...
```

### Test Organization

```
tests/
├── unit/           # Fast, isolated tests (mock dependencies)
├── integration/    # Tests with real dependencies (DB, APIs)
├── e2e/            # Full workflow tests
└── rag_evaluation/ # RAG quality tests
```

### Running Quality Checks

Before opening a PR, run all checks locally:

```bash
# Linting (automated style enforcement)
uv run ruff check src/ tests/ --fix
uv run ruff format src/ tests/

# Type checking (catches type errors in strict mode)
uv run mypy src/ --strict

# Tests with coverage (ensures functionality & quality)
uv run pytest --cov=src --cov-report=term-missing --cov-fail-under=80

# Security audit (detects vulnerable dependencies)
uv run pip-audit
```

**All-in-one command:**
```bash
uv run ruff check src/ tests/ --fix && \
uv run ruff format src/ tests/ && \
uv run mypy src/ --strict && \
uv run pytest --cov=src --cov-fail-under=80
```

**What each tool does:**
- **ruff** — Fast Python linter and formatter (replaces flake8, black, isort)
- **mypy** — Static type checker (catches type errors before runtime)
- **pytest** — Testing framework with coverage reporting
- **pip-audit** — Scans for known security vulnerabilities

See [docs/development-standards.md](docs/development-standards.md) for the complete testing guide.

## Commit Messages

We use [Conventional Commits](https://www.conventionalcommits.org/) for clear, scannable history.

### Format

```
<type>: <description>
```

- Lowercase
- Imperative mood ("add" not "added")
- No period at the end
- Keep under 72 characters

### Types

- `feat:` — New feature
- `fix:` — Bug fix
- `docs:` — Documentation changes
- `test:` — Adding or updating tests
- `refactor:` — Code improvements (no functionality change)
- `chore:` — Maintenance (dependencies, tooling)

### Examples

```
feat: add semantic caching for RAG queries
fix: resolve timeout in document chunking
docs: update API endpoint examples
test: add coverage for hallucination detection
refactor: extract LLM provider interface
chore: update dependencies to latest versions
```

## Submitting a Pull Request

### Process

1. **Push your branch** to your fork
2. **Open a PR** against the `main` branch
3. **Fill out the PR description:**
   - What problem does this solve?
   - How was it tested?
   - Any breaking changes?
4. **Wait for review** (typically 1-2 days)
5. **Respond to feedback** and make requested changes
6. **Maintainer will squash merge** once approved

### PR Checklist

Before submitting, ensure:

- [ ] All tests pass locally (`uv run pytest`)
- [ ] New code has tests (80% coverage)
- [ ] Types check (`uv run mypy src/ --strict`)
- [ ] Linting passes (`uv run ruff check && ruff format`)
- [ ] No secrets or API keys committed
- [ ] Documentation updated (if needed)
- [ ] ADR added for significant architectural decisions

### Review Requirements

- **1 approval required**
- **CI must pass** (all checks green)
- **Squash merge** to maintain clean history

## Getting Help

### Questions?

- **Open a GitHub issue** or discussion
- **Check existing issues** first—someone may have already asked
- **Include context:** what you tried, error messages, environment details

### Where to Find Things

- **Architecture overview** → [docs/architecture.md](docs/architecture.md)
- **Quick patterns** → [CLAUDE.md](CLAUDE.md)
- **Deployment guide** → [docs/guides/deployment.md](docs/guides/deployment.md)
- **Decision context** → [docs/decisions/](docs/decisions/)
- **API documentation** → `/docs` endpoint (OpenAPI/Swagger)

### Setup Issues?

- Verify `.env` has all required API keys (check `.env.example`)
- Make sure you're using Python 3.13+
- Try `uv sync --extra dev` to reinstall dependencies
- Check the [README](README.md) configuration section

## License

By contributing to Retriever, you agree that your contributions will be licensed under the [MIT License](LICENSE).

---

**Thank you for contributing!** Questions? Don't hesitate to open an issue—we're here to help make your first contribution a great experience.

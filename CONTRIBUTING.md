# Contributing to Retriever

Retriever is an AI-powered Q&A system using RAG (Retrieval-Augmented Generation) to help users find information in organizational documents. Contributions of all kinds are welcome — bug fixes, features, documentation, and tests.

## Quick Start

```bash
# Clone (or fork first, then clone your fork)
git clone https://github.com/your-org/retriever.git
cd retriever
cp .env.example .env
# Edit .env — add your API keys (see Environment Configuration below)

# Start infrastructure
supabase start
docker compose up -d

# Backend
cd backend
uv sync --dev
uv run alembic upgrade head
uv run uvicorn retriever.main:app --reload --port 8000
# → http://localhost:8000/health

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

## Prerequisites

- **Python 3.13+** with [uv](https://docs.astral.sh/uv/)
- **Node.js 22+** with npm
- **Docker** (for postgres + jaeger via `docker compose`)
- **[Supabase CLI](https://supabase.com/docs/guides/cli)** (for local auth)
- **API keys:**
  - [OpenRouter](https://openrouter.ai/keys) — LLM access
  - [OpenAI](https://platform.openai.com/api-keys) — embeddings and moderation

## Environment Configuration

1. Copy `.env.example` to `.env`
2. Add your API keys:

```bash
OPENROUTER_API_KEY=your-key-here
OPENAI_API_KEY=your-key-here
```

3. The remaining defaults work for local development:
   - `DATABASE_URL` points to `localhost:5432` (docker compose postgres)
   - `SUPABASE_URL` / `SUPABASE_ANON_KEY` — update with values from `supabase status` after `supabase start`
   - Cloudflare, Langfuse, and GCP settings are optional (features degrade gracefully without them)

## Day-to-Day Development

```bash
# Start infrastructure
supabase start
docker compose up -d

# Backend (terminal 1)
cd backend
uv run uvicorn retriever.main:app --reload --port 8000

# Frontend (terminal 2)
cd frontend
npm run dev

# Stop everything
docker compose down
supabase stop
```

## Quality Checks (before PR)

### Backend (run from `backend/`)

```bash
# Linting and formatting
uv run ruff check src/ tests/ --fix
uv run ruff format src/ tests/

# Type checking (strict mode — use python -m mypy, NOT uv run mypy)
uv run python -m mypy src/ --strict

# Tests with coverage (80% minimum)
uv run python -m pytest tests/ --cov=src/retriever --cov-report=term-missing --cov-fail-under=80

# Security audit
uv run pip-audit

# All-in-one
uv run ruff check src/ tests/ --fix && uv run ruff format src/ tests/ && \
uv run python -m mypy src/ --strict && \
uv run python -m pytest tests/ --cov=src/retriever --cov-fail-under=80
```

### Frontend (run from `frontend/`)

```bash
# Type checking (TypeScript + Svelte)
npm run check

# Production build
npm run build

# E2E tests (requires build first)
npm run test:e2e
```

## Making Changes

We use **GitHub Flow**: feature branches → pull request → squash merge to `main`.

### Workflow

1. **Start from main:**
   ```bash
   git checkout main && git pull origin main
   ```

2. **Create a feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Branch naming:**
   - `feature/` — New features
   - `fix/` — Bug fixes
   - `docs/` — Documentation
   - `refactor/` — Code improvements
   - `test/` — Tests
   - `chore/` — Maintenance

4. **Commit, push, and open a PR** against `main`.

### Commit Messages (Conventional Commits)

```
<type>: <description>
```

Lowercase, imperative mood, no period, under 72 characters.

Types: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`

## Code Standards

- **Type hints required** on all function signatures (including return types)
- **Docstrings** (Google style) on public APIs and non-trivial functions
- **Error handling** — no bare `except:`, chain with `from` for context
- **Security** — never commit secrets; store in environment variables; validate user input

## Testing

- **80% coverage minimum** for new code
- **Naming:** `test_<function>_<scenario>_<expected>`
- **Organization:** `tests/unit/`, `tests/integration/`, `tests/e2e/`

## PR Checklist

- [ ] All backend quality checks pass
- [ ] Frontend checks pass (`npm run check && npm run build`)
- [ ] New code has tests (80% coverage)
- [ ] No secrets or API keys committed
- [ ] Documentation updated if needed

**Review:** 1 approval required, CI must pass, squash merge.

## VS Code Setup (optional)

Recommended extensions:
- Python + Pylance
- Svelte for VS Code
- ESLint
- Tailwind CSS IntelliSense

Debug config (F5) and quality check tasks (Ctrl+Shift+P → Run Task) are preconfigured in `.vscode/`.

## Project Structure

```
retriever/
├── backend/           # FastAPI + SQLAlchemy + pgvector (active development)
│   ├── src/retriever/ # Application source
│   └── tests/         # Backend tests
├── frontend/          # SvelteKit + Svelte 5 + Skeleton UI (active development)
│   └── src/           # SvelteKit source
└── docs/              # Architecture docs and ADRs
```

## Understanding the Codebase

- **Quick patterns & conventions** → [CLAUDE.md](CLAUDE.md)
- **Architecture deep dive** → [docs/architecture.md](docs/architecture.md)
- **Implementation roadmap** → [docs/increments.md](docs/increments.md)
- **API documentation** → `/docs` endpoint (OpenAPI/Swagger)

## Getting Help

- Check existing [issues](https://github.com/your-org/retriever/issues) first
- Open a new issue with context: what you tried, error messages, environment details
- See [CLAUDE.md](CLAUDE.md) for gotchas and non-obvious patterns

## License

By contributing to Retriever, you agree that your contributions will be licensed under the [MIT License](LICENSE).

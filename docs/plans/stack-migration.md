# Retriever Stack Migration — Implementation Plan

## Context

Migrating Retriever from server-rendered monolith (FastAPI + Jinja2/HTMX + SQLite + ChromaDB) to a monorepo with FastAPI backend (Cloud Run) + SvelteKit frontend (Cloudflare Pages), Supabase Postgres+pgvector, Supabase Auth, Cloudflare AI Gateway, and full observability.

**Approach:** Fast prototype each iteration → validate with user/browser → then build production-quality code. Agile: logical chunks, tested on each iteration. Existing SQLite data is not important.

## Status

- **Phase 0:** COMPLETE — Accounts provisioned, env vars in `env-services.md`
- **Branch:** `worktree-elegant-nibbling-snowflake`

## Workflow Rules

1. **uv only** for Python dependency management (`uv venv`, `uv sync`, `uv run`)
2. **No Datadog, no Sentry for MVP** — use GCP Cloud Trace + Error Reporting (free with Cloud Run). File ADR for this deviation from tech-stack standard.
3. **Langfuse stays** for LLM-specific observability (token costs, prompt traces)
4. **Logical commits** — never commit before running all tests + user review. Squash-rebase on merges with user approval
5. **Code review** — run `code-simplifier:code-simplifier` and `feature-dev:code-reviewer` before presenting to user
6. **Docs always current** — update README.md, CLAUDE.md, CHANGELOG, CONTRIBUTING with each commit
7. **Local preview** — app must run locally via docker-compose (backend + frontend + Postgres)
8. **Test documents** — git-untracked `documents/` directory for loading test docs (in .gitignore)
9. **Multi-tenancy ready** — `tenant_id` on all tables from day 1, RLS includes tenant scope
10. **PEP8** — Python 3.13+, proper `src/retriever/` package namespace

## Environment Variables

Move `env-services.md` contents to `.env` (gitignored). Production secrets go in **GCP Secret Manager**, mounted via `gcloud run deploy --set-secrets`.

| Service | Env Var | Config Field | Secret? |
|---------|---------|-------------|---------|
| Supabase | `SUPABASE_URL` | `supabase_url` | No (public) |
| Supabase | `SUPABASE_ANON_KEY` | `supabase_anon_key` | No (public) |
| Supabase | `SUPABASE_SERVICE_ROLE_KEY` | `supabase_service_role_key` | **Yes** |
| Supabase | `DATABASE_URL` | `database_url` | **Yes** (has password) |
| OpenRouter | `OPENROUTER_API_KEY` | `openrouter_api_key` | **Yes** |
| OpenAI | `OPENAI_API_KEY` | `openai_api_key` | **Yes** |
| Langfuse | `LANGFUSE_SECRET_KEY` | `langfuse_secret_key` | **Yes** |
| Langfuse | `LANGFUSE_PUBLIC_KEY` | `langfuse_public_key` | No |
| Langfuse | `LANGFUSE_HOST` | `langfuse_host` | No |
| Cloudflare | `CLOUDFLARE_ACCOUNT_ID` | `cloudflare_account_id` | No |
| Cloudflare | `CLOUDFLARE_GATEWAY_ID` | `cloudflare_gateway_id` | No |
| GCP | `GCP_PROJECT_ID` | (deployment only) | No |

All `Secret? = Yes` fields use `SecretStr` in pydantic-settings.

---

## Architecture Decisions (from expert review)

### Package Layout: `backend/src/retriever/` (not `backend/src/`)
No uv workspace — single Python project in `backend/`, frontend is separate Node project. Import path: `from retriever.config import Settings`. Uvicorn: `retriever.main:app`.

```
backend/
├── pyproject.toml        # name = "retriever"
├── src/
│   └── retriever/        # importable package
│       ├── __init__.py
│       ├── main.py
│       ├── config.py
│       └── ...
├── tests/
├── alembic/
└── Dockerfile
```

### Auth: JWKS Validation (not shared secret)
Validate Supabase JWTs via JWKS endpoint (`https://<ref>.supabase.co/.well-known/jwks.json`), not the JWT secret. Use `PyJWT[crypto]` with `jwt.PyJWKClient`. Algorithm: RS256. Admin role via `app_metadata.is_admin` (not `user_metadata`).

### Database Connection: Pooler + SSL
- Use Supabase connection pooler (port 6543), not direct (port 5432)
- Enforce SSL: `?sslmode=require` in DATABASE_URL
- asyncpg prepared statement fix: `connect_args={"prepared_statement_cache_size": 0}`
- `expire_on_commit=False` on all async sessions (mandatory for SQLAlchemy async)
- `pool_pre_ping=True` for Cloud Run cold starts

### RLS: Every Table, Default Deny
Enable RLS on ALL tables in `public` schema. Policies:
- `users`: service role only
- `messages`: `auth.uid() = user_id AND tenant_id = current_setting('app.tenant_id')`
- `documents`: authenticated read, admin write (via `app_metadata.is_admin`)
- `document_chunks`: authenticated read
- `semantic_cache`: authenticated read, service role write
Consider moving `document_chunks` and `semantic_cache` to non-public schema (backend-only access).

### Multi-Tenancy: tenant_id from Day 1
`tenant_id UUID NOT NULL` on every data table (users, messages, documents, document_chunks, semantic_cache). Default to a constant UUID for MVP. All indexes include tenant_id. All RLS policies scope by tenant_id. All pgvector queries include `WHERE tenant_id = :tid`.

### Observability: Bootstrap in Phase 1
Split observability:
- **Phase 1:** structlog JSON config + OTel with console exporter (immediate dev visibility)
- **Phase 6:** GCP Cloud Trace exporter + Langfuse (needs deployed Cloud Run)
- **Local dev:** Console/Jaeger exporter via docker-compose

### No `supabase` Python SDK
Use `PyJWT[crypto]` for JWT validation + `asyncpg`/SQLAlchemy for DB access. The full `supabase` SDK pulls in unnecessary deps (gotrue, postgrest, storage3, realtime).

### CORS: Explicit Origins
`CORSMiddleware` with explicit `allow_origins` per environment. Never `["*"]` with credentials. Frontend origin: `localhost:5173` (dev), Cloudflare Pages domain (prod).

### Rate Limiting: Cloud Run Concurrency + Cloudflare
MVP: `--concurrency=80 --max-instances=2` on Cloud Run + Cloudflare rate limiting rules on frontend. Document upload: explicit 5/min limit.

### File Upload: Content Validation
Validate UTF-8 content (not just extension). Preserve `Path().name` path traversal defense. Set `Content-Disposition: attachment` on serve-back. XSS sanitization on markdown rendering in SvelteKit (DOMPurify/rehype-sanitize).

### Testing: Local Postgres Only
Tests run against local Postgres via docker-compose (`pgvector/pgvector:pg17` on port 5433, tmpfs-backed). Never test against live Supabase. CI uses GitHub Actions Postgres service container.

---

## Target Monorepo Structure

```
retriever/
├── backend/
│   ├── pyproject.toml          # name = "retriever", standalone uv project
│   ├── src/
│   │   └── retriever/          # importable package
│   │       ├── __init__.py
│   │       ├── main.py
│   │       ├── config.py
│   │       ├── models/         # SQLAlchemy 2.0 async models
│   │       ├── modules/
│   │       │   ├── auth/       # Supabase Auth (JWKS validation)
│   │       │   ├── rag/        # RAG pipeline
│   │       │   └── documents/  # Document management
│   │       ├── infrastructure/
│   │       │   ├── vectordb/   # pgvector
│   │       │   ├── cache/      # pgvector semantic cache
│   │       │   ├── embeddings/ # OpenAI embeddings (via AI Gateway)
│   │       │   ├── llm/        # LLM provider (via AI Gateway)
│   │       │   ├── observability/  # structlog + OTel + GCP
│   │       │   └── safety/     # Content moderation
│   │       └── api/            # REST API routes
│   ├── alembic/
│   ├── tests/
│   ├── alembic.ini
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── routes/
│   │   ├── lib/
│   │   └── app.html
│   ├── package.json
│   ├── svelte.config.js
│   └── wrangler.toml
├── documents/                  # Test documents (gitignored)
├── docker-compose.yml          # Local dev: backend + frontend + postgres
├── docker-compose.test.yml     # Test postgres (tmpfs-backed)
├── .devcontainer/
├── .github/workflows/
├── .env                        # Local secrets (gitignored)
├── .env.example                # Template (no real values)
├── CLAUDE.md
├── README.md
├── CONTRIBUTING.md
└── CHANGELOG.md
```

---

## Phase 0: Account Provisioning — COMPLETE

Keys in `env-services.md`, will be moved to `.env`.

## Phase 0b: GCP Setup (via gcloud CLI)

```bash
# 1. Create or select project
gcloud projects create retriever-prod --name="Retriever" 2>/dev/null || gcloud config set project retriever-prod

# 2. Enable required APIs
gcloud services enable run.googleapis.com artifactregistry.googleapis.com \
  iamcredentials.googleapis.com cloudtrace.googleapis.com clouderrorreporting.googleapis.com

# 3-7. WIF pool, OIDC provider, service account, role bindings
# (see previous plan version for full commands)
# GitHub repo: ckrough/retriever
```

Claude will run these commands and capture values.

---

## Phase 1: Backend Skeleton + Local Dev Stack

**Goal:** Minimal FastAPI app with `/health`, CORS, structlog+OTel bootstrap, docker-compose with Postgres, all running locally.

### Iteration 1a: Project Setup + Health Endpoint
1. `backend/pyproject.toml` — standalone uv project (no workspace):
   - `name = "retriever"`, `requires-python = ">=3.13"`, hatchling build
   - Deps: `fastapi>=0.135`, `uvicorn[standard]`, `pydantic>=2.10`, `pydantic-settings>=2.6`, `structlog>=24.4`, `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-instrumentation-fastapi`
   - Dev deps: `pytest`, `pytest-asyncio`, `pytest-cov`, `httpx>=0.28`, `respx`, `mypy`, `ruff`, `pip-audit`
   - Hatch config: `packages = ["src/retriever"]`
   - Ruff: `src = ["src"]`, `known-first-party = ["retriever"]`, target py313, line-length 88
   - Mypy: strict, `mypy_path = "src"`
2. `backend/src/retriever/__init__.py` — empty
3. `backend/src/retriever/config.py` — pydantic-settings with all env vars, `SecretStr` for secrets, computed `ai_gateway_base_url`
4. `backend/src/retriever/main.py` — FastAPI with lifespan, `/health`, `CORSMiddleware` (explicit origins)
5. `backend/tests/test_health.py`
6. `cd backend && uv venv && uv sync && uv run pytest`

### Iteration 1b: Observability Bootstrap + Docker
1. `backend/src/retriever/infrastructure/observability/` — structlog JSON config, OTel console exporter
2. `backend/Dockerfile` — 2-stage uv build, `libpq5`, non-root user
3. `backend/entrypoint.sh` — exec uvicorn
4. `docker-compose.yml` at root — backend + `pgvector/pgvector:pg17` (dev) + frontend placeholder
5. `docker-compose.test.yml` — Postgres on port 5433, tmpfs-backed
6. `.env` (from env-services.md), `.env.example`, `.gitignore` updates
7. `documents/` directory (gitignored)

### Patterns to Reuse
| Pattern | Source | Details |
|---------|--------|---------|
| Settings | `src/config.py` | `BaseSettings` + `SettingsConfigDict` + `@lru_cache` |
| Health | `src/api/health.py` | `HealthResponse`, `Literal["healthy","unhealthy"]`, 503 on failure |
| Dockerfile | `Dockerfile` | 2-stage uv build, non-root user, entrypoint.sh exec |
| Lifespan | `src/main.py` | `@asynccontextmanager` lifespan |

### Verification
```bash
cd backend && uv run ruff check src/ tests/ && uv run mypy src/ --strict && uv run pytest
docker compose up  # Backend + Postgres running
curl http://localhost:8000/health  # 200
```

---

## Phase 2: Frontend Skeleton

**Goal:** SvelteKit + Svelte 5 runes + Skeleton UI + Tailwind 4, running locally.

### Files to Create
- `frontend/package.json` — svelte 5, sveltekit 2, skeleton-svelte, tailwindcss 4, @supabase/supabase-js, @sveltejs/adapter-cloudflare
- `frontend/svelte.config.js` — Cloudflare adapter
- `frontend/vite.config.ts`, `frontend/tsconfig.json`
- `frontend/src/app.html`, `frontend/src/app.css` (Tailwind 4 + Skeleton theme)
- `frontend/src/routes/+layout.svelte` — Skeleton AppShell
- `frontend/src/routes/+page.svelte` — "Retriever" placeholder
- `frontend/src/lib/supabase.ts` — Supabase client (uses `PUBLIC_SUPABASE_URL`, `PUBLIC_SUPABASE_ANON_KEY`)
- `frontend/wrangler.toml`
- Add frontend service to `docker-compose.yml`

**Must use Svelte 5 runes.** No Svelte 4 store syntax.
**XSS protection:** Use `rehype-sanitize` or `DOMPurify` for any markdown rendering.

### Verification
```bash
cd frontend && npm install && npm run dev   # http://localhost:5173
npm run build && npm run check
```

---

## Phase 3: Database (Supabase Postgres + pgvector)

**Critical path.** Fresh schema only — no data migration needed.

### 3a: SQLAlchemy Models + Alembic
- `backend/src/retriever/models/base.py`:
  - `DeclarativeBase`, async engine factory with pooler URL, `ssl=True`, `prepared_statement_cache_size=0`
  - `async_sessionmaker(expire_on_commit=False)`
  - `pool_pre_ping=True`, configurable `pool_size`/`max_overflow`
- Models with `Mapped[]` typed columns (passes mypy strict):
  - `user.py`: `id UUID PK`, `email`, `tenant_id`, `is_admin`, `created_at TIMESTAMPTZ`
  - `message.py`: `id UUID PK`, `user_id`, `tenant_id`, `role`, `content`, `created_at`
  - `document.py`: `id UUID PK`, `filename`, `tenant_id`, `title`, `file_path`, `is_indexed`, `created_at`, `updated_at`
- `alembic init -t async` for async env.py
- `001_initial_schema.py` — all tables with `tenant_id UUID NOT NULL`, composite indexes include tenant_id
- **All tables get `ENABLE ROW LEVEL SECURITY`** in migration

### 3b: pgvector Vector Storage
- `002_vector_storage.py`:
  - `CREATE EXTENSION IF NOT EXISTS vector`
  - `document_chunks` table: id, content, `embedding vector(1536)`, metadata JSONB, source, section, title, tenant_id, created_at
  - HNSW index (`m=16, ef_construction=64`): `CREATE INDEX ... USING hnsw (embedding vector_cosine_ops)`
  - tsvector column: `content_tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED`
  - GIN index on `content_tsv`
  - All indexes include `tenant_id`
- `backend/src/retriever/infrastructure/vectordb/pgvector.py` implementing `VectorStore` protocol
  - All queries include `WHERE tenant_id = :tid`

### 3c: Semantic Cache
- `003_semantic_cache.py`: `semantic_cache` table with `vector(1536)`, tenant_id, HNSW index
- `backend/src/retriever/infrastructure/cache/pg_cache.py` implementing `SemanticCache` protocol

### 3d: Repository Implementations (SQLAlchemy async)
- Port auth, documents, message_store repos from raw SQL → SQLAlchemy
- FastAPI DI: `Depends(get_session)` pattern with commit/rollback

### 3e: Hybrid Retrieval with tsvector
- Replace `rank-bm25` with `ts_rank` + `plainto_tsquery` SQL
- Keep RRF fusion logic unchanged

### RLS Policies (Alembic migration or Supabase dashboard)
- `messages`: `SELECT/INSERT/UPDATE/DELETE WHERE auth.uid() = user_id AND tenant_id = ...`
- `documents`: `SELECT` for authenticated, `INSERT/UPDATE/DELETE` for admin (`app_metadata->>'is_admin' = 'true'`)
- `document_chunks`: `SELECT` for authenticated (or move to non-public schema)
- `semantic_cache`: `SELECT` for authenticated, mutations for service role (or non-public schema)

### Verification
```bash
docker compose -f docker-compose.test.yml up -d
cd backend && uv run alembic upgrade head
uv run pytest tests/ -k "repository or store or cache or vectordb"
```

---

## Phase 4: Auth (Supabase Auth + JWKS)

- `PyJWT[crypto]` + `jwt.PyJWKClient` for JWKS validation (RS256)
- Admin check: `payload["app_metadata"]["is_admin"]`
- FastAPI dependencies: `require_auth`, `require_admin`
- No `supabase` Python SDK needed
- Frontend: `@supabase/supabase-js` for login/signup flows

---

## Phase 5: LLM Gateway (Cloudflare AI Gateway)

Config change only — `AsyncOpenAI(base_url=ai_gateway_base_url)`.
Also route moderation API through gateway for unified logging.

**Must complete before Phase 7** (RAG pipeline needs LLM calls).

---

## Phase 6: Observability (GCP Native + Langfuse)

Bootstrap (structlog + OTel console) already in Phase 1. This phase adds production exporters:

### 6a: GCP Cloud Trace Exporter
- `opentelemetry-exporter-gcp-trace` replaces console exporter in production
- `opentelemetry-resourcedetector-gcp` for Cloud Run metadata
- structlog adds `trace_id`/`span_id` for log-trace correlation
- Cloud Logging auto-ingests stdout JSON (zero config)
- Cloud Monitoring alerts on error rate, latency p99

### 6b: Langfuse
- `@observe()` on LLM calls, inject OTel trace_id for cross-correlation
- Token counting and cost tracking

### 6c: Local Dev
- Jaeger container in docker-compose for local trace visualization
- Console fallback when Jaeger unavailable

### ADR Required
File ADR documenting deviation from tech-stack standard (GCP native vs Datadog+Sentry). Rationale: cost ($0 vs $50-110+/mo), vendor consolidation, OTel-first architecture makes switching trivial.

---

## Phase 7: RAG Pipeline Port

**Depends on:** Phase 3 (DB), Phase 4 (Auth), Phase 5 (LLM Gateway)

Port business logic with new infrastructure. Pure Python modules copy unchanged. Service layer swaps DI wiring.

### REST API Endpoints
- `POST /api/v1/ask` — JSON Q&A (auth required)
- `POST /api/v1/documents/upload` — File upload (admin, 5/min limit)
- `POST /api/v1/documents/{id}/index` — Trigger indexing (admin)
- `GET /api/v1/documents` — List (auth required)
- `DELETE /api/v1/documents/{id}` — Delete (admin)
- `GET /api/v1/history` — Conversation history (user-scoped)
- `DELETE /api/v1/history` — Clear (user-scoped)

### Safety Stack
Port all three layers: prompt injection detection, OpenAI moderation, hallucination detection.
Add monitoring alerts for moderation timeouts/errors. Document fail-open behavior in ADR.

### File Upload Security
- Content validation (UTF-8 for .md/.txt), not just extension check
- `Path().name` path traversal defense
- Ephemeral filesystem on Cloud Run: process-and-discard (chunks+embeddings persist, raw file does not) OR Supabase Storage for permanent storage. Decision needed.
- `Content-Disposition: attachment` on serve-back

### `/health` Enhancement
Check Postgres connectivity (`SELECT 1`) and pgvector extension (`SELECT vector_dims(NULL::vector)`).

---

## Phase 8: SvelteKit Frontend

Feature parity with existing HTMX UI first, enhance later.

| Route | Purpose |
|-------|---------|
| `/` | Chat interface |
| `/login` | Supabase Auth UI |
| `/admin` | Document management |

Components: ChatMessage, CitationCard, ErrorMessage, MessageHistory, DocumentUpload, DocumentList.
Markdown rendering with XSS sanitization (`rehype-sanitize` or `DOMPurify`).

---

## Phase 9: CI/CD + DevContainer

### CI (`ci.yml` on PR)
- Backend: ruff, mypy, pytest (Postgres service container), `pip-audit`
- Frontend: eslint, svelte-check, vitest, Playwright, `npm audit`
- `anthropics/claude-code-action@v1` for `@claude` PR mentions

### Deploy Backend (`deploy-backend.yml` on push to main)
- `google-github-actions/auth@v3` (WIF)
- `gcloud run deploy --source ./backend --set-secrets=...`
- Hurl smoke tests post-deploy

### Deploy Frontend (`deploy-frontend.yml`)
- `cloudflare/wrangler-action@v3`
- Build-time env vars: `PUBLIC_SUPABASE_URL`, `PUBLIC_SUPABASE_ANON_KEY`

### DevContainer
- `.devcontainer/devcontainer.json` using `docker-compose.yml`
- One-command `docker compose up` for full local stack

---

## Phase 10: Cleanup

Remove `src/` (old monolith), root `Dockerfile`, old workflows.
Add `fast-llms-txt` middleware, `openapi-llm`.
Update all docs. Ensure `.env.example` has no real values.

### Graceful Shutdown
Lifespan handler: `engine.dispose()`, `TracerProvider.shutdown()`, `langfuse.flush()`.

---

## Future: Multi-Tenancy & Whitelabelling

Schema is ready (`tenant_id` on all tables, RLS scoped). Future work:
- `tenants` table with `id`, `name`, `config_json` (branding, feature flags)
- Subdomain-based tenant resolution (preferred for security)
- Separate document collections per tenant via `WHERE tenant_id = :tid`
- Config-driven branding (logo, colors, app name)

---

## Phase Execution Order

```
Phase 0b (GCP) ──────────────────────────────────────────────────────────────
    │
    ├──→ Phase 1 (Backend + Docker) ──→ Phase 3 (Database) ──→ Phase 4 (Auth)
    │                                       │                      │
    │                                       │            Phase 5 (LLM GW) ──→ Phase 7 (RAG)
    │                                       │                                      │
    ├──→ Phase 2 (Frontend) ──────────────────────────────────────→ Phase 8 (Frontend)
    │                                       │                                      │
    ├──→ Phase 6 (GCP exporters) ← after Phase 1 bootstrap                        │
    │                                                                              v
    └──────────────────────────────────────────────────────────────→ Phase 9 (CI/CD)
                                                                                   │
                                                                                   v
                                                                             Phase 10 (Cleanup)
```

**Critical path:** Phase 1 → 3 → 4 → 5 → 7 → 8 → 9 → 10
**Parallel:** Phases 1+2. Phase 6 after Phase 1.

---

## Pre-Implementation Housekeeping

1. Move `env-services.md` → `.env`, ensure `.env` + `documents/` in `.gitignore`
2. Create `.env.example` (placeholder values only, never real keys)
3. File ADR: GCP observability instead of Datadog+Sentry

## Quality Gates (Every Iteration)

```bash
cd backend && uv run ruff check src/ tests/ --fix
cd backend && uv run ruff format src/ tests/
cd backend && uv run mypy src/ --strict
cd backend && uv run pytest tests/ --cov=src/retriever --cov-fail-under=80
cd backend && uv run pip-audit
```

Then: code-simplifier → code-reviewer → user review → commit.

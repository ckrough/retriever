# Pre-PR Testing Script — Stack Migration

Runnable verification plan for the `worktree-elegant-nibbling-snowflake` branch before opening the PR. Covers all layers: backend automated gates, manual API testing, frontend gates, UI testing, full-stack integration, CI/CD verification, and cleanup.

**Branch:** `worktree-elegant-nibbling-snowflake`
**Scope:** Phases 1–10 of the stack migration (FastAPI backend, SvelteKit frontend, pgvector, Supabase Auth, CI/CD, legacy monolith removal)

---

## Phase 0: Prerequisites & Environment Setup

### 0.1 Required tools

```bash
python3 --version    # 3.13+
uv --version         # any recent version
node --version       # 22+
docker --version     # Docker Desktop or colima
supabase --version   # Supabase CLI
```

### 0.2 Environment files

**Backend (`.env` in project root):**

```bash
cp .env.example .env
```

Edit `.env` — fill in at minimum:

| Variable | Required For | Source |
|----------|-------------|--------|
| `DATABASE_URL` | DB connection | Default `localhost:5432` works with docker compose |
| `SUPABASE_URL` | Auth | `supabase status` → API URL (usually `http://127.0.0.1:54321`) |
| `SUPABASE_ANON_KEY` | Auth | `supabase status` → anon key |
| `OPENROUTER_API_KEY` | LLM completions | [openrouter.ai/keys](https://openrouter.ai/keys) |
| `OPENAI_API_KEY` | Embeddings + moderation | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |

Leave `LANGFUSE_*`, `CLOUDFLARE_*`, `GCP_PROJECT_ID` at defaults — features degrade gracefully without them.

**Frontend (`frontend/.env`):**

Already committed for local dev. Verify contents match your local Supabase:

```
PUBLIC_SUPABASE_URL=http://127.0.0.1:54321
PUBLIC_SUPABASE_ANON_KEY=<anon key from supabase status>
PUBLIC_API_BASE_URL=http://localhost:8000
```

### 0.3 Start infrastructure

```bash
# From worktree root
supabase start
# Note output — copy ANON KEY and API URL into .env files if needed

docker compose up -d
# Verify postgres (5432) and jaeger (16686) are running:
docker compose ps
```

**Expected:** Two services healthy — `postgres` on 5432, `jaeger` on 16686 (UI) and 4317 (OTLP gRPC).

---

## Phase 1: Backend Automated Quality Gates

All commands run from `backend/`.

### 1.1 Install dependencies

```bash
cd backend
uv sync --dev
```

### 1.2 Linting

```bash
uv run ruff check src/ tests/ --fix
uv run ruff format src/ tests/ --check
```

**Pass criteria:** Zero errors, zero reformatted files.

### 1.3 Type checking

```bash
uv run python -m mypy src/ --strict
```

**Pass criteria:** `Success: no issues found`

> **Important:** Use `python -m mypy`, NOT `uv run mypy`. The mypy binary is not on PATH in the uv venv.

### 1.4 Unit tests + coverage

```bash
# Start test database (uses port 5433, tmpfs for speed)
docker compose -f docker-compose.test.yml up -d

# Wait for healthcheck
sleep 5

uv run python -m pytest tests/ --cov=src/retriever --cov-report=term-missing --cov-fail-under=80
```

**Pass criteria:** All tests pass, coverage >= 80%.

### 1.5 Security audit

```bash
uv run pip-audit
```

**Pass criteria:** No known vulnerabilities (informational warnings OK).

### 1.6 All-in-one gate

```bash
uv run ruff check src/ tests/ --fix && \
uv run ruff format src/ tests/ --check && \
uv run python -m mypy src/ --strict && \
uv run python -m pytest tests/ --cov=src/retriever --cov-fail-under=80
```

---

## Phase 2: Backend Manual Testing

### 2.1 Start the backend

```bash
cd backend
uv run alembic upgrade head     # Apply all 5 migrations
uv run uvicorn retriever.main:app --reload --port 8000
```

### 2.2 Health endpoint

```bash
curl -s http://localhost:8000/health | python3 -m json.tool
```

**Expected:**

```json
{
    "status": "healthy",
    "version": "2.0.0",
    "database": "connected",
    "pgvector": "available"
}
```

- [x] `status` is `"healthy"` (not `"degraded"`)
- [x] `database` is `"connected"`
- [x] `pgvector` is `"available"`

### 2.3 OpenAPI docs

Open in browser: **http://localhost:8000/docs**

- [x] Swagger UI loads
- [x] Endpoint groups visible: `health`, `rag`, `documents`, `messages`
- [x] Request/response schemas render correctly
- [x] "Try it out" buttons present

### 2.4 Auth — unauthenticated requests rejected

```bash
# All protected endpoints should return 401
curl -s -o /dev/null -w "%{http_code}" \
  http://localhost:8000/api/v1/ask -X POST \
  -H "Content-Type: application/json" -d '{"question":"test"}'
# Expected: 401

curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/history
# Expected: 401

curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/documents
# Expected: 401

curl -s -o /dev/null -w "%{http_code}" \
  http://localhost:8000/api/v1/documents/upload -X POST
# Expected: 401

curl -s -o /dev/null -w "%{http_code}" \
  http://localhost:8000/api/v1/documents/00000000-0000-0000-0000-000000000000 -X DELETE
# Expected: 401
```

- [x] `/api/v1/ask` → 401
- [x] `/api/v1/history` → 401
- [x] `/api/v1/documents` → 401
- [x] `/api/v1/documents/upload` → 401
- [x] `/api/v1/documents/{id}` DELETE → 401

### 2.5 Auth — get a test token

```bash
# Get the local publishable key (called "anon key" in older Supabase CLI versions)
ANON_KEY=$(supabase status 2>/dev/null | grep 'Publishable' | awk '{print $NF}')

# Sign up a test user
curl -s http://127.0.0.1:54321/auth/v1/signup \
  -H "apikey: $ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpass123"}' | python3 -m json.tool

# Sign in and capture access_token
TOKEN=$(curl -s "http://127.0.0.1:54321/auth/v1/token?grant_type=password" \
  -H "apikey: $ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpass123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

echo "TOKEN=$TOKEN"
```

- [x] Signup returns user object (email confirmations are disabled in local Supabase)
- [x] Sign-in returns `access_token`

### 2.6 Auth — authenticated requests succeed

```bash
# Get history (should be empty initially)
curl -s http://localhost:8000/api/v1/history \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

**Expected:** `{"messages": [], "count": 0}`

```bash
# List documents (should be empty)
curl -s http://localhost:8000/api/v1/documents \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

**Expected:** `{"documents": [], "count": 0}`

- [x] History returns empty list with count 0
- [x] Documents returns empty list with count 0

### 2.7 RAG ask endpoint

> **Requires** valid `OPENROUTER_API_KEY` and `OPENAI_API_KEY` in `.env`.

```bash
curl -s http://localhost:8000/api/v1/ask \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question":"What are the shelter policies?"}' | python3 -m json.tool
```

**Expected:** JSON with fields:

- `answer` — string (should indicate insufficient context if no documents indexed)
- `chunks_used` — list (empty if no documents)
- `confidence_level` — string (`"high"`, `"medium"`, or `"low"`)
- `confidence_score` — float
- `blocked` — boolean
- `blocked_reason` — null or string

- [x] Response returns 200
- [x] All expected fields present
- [x] No crash with empty vector store

### 2.8 Conversation history persistence

```bash
# After asking a question, history should have entries
curl -s http://localhost:8000/api/v1/history \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

**Expected:** `count` of 2 (user question + assistant answer), each message has `id`, `role`, `content`, `created_at`.

```bash
# Clear history
curl -s -X DELETE http://localhost:8000/api/v1/history \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

**Expected:** `{"deleted_count": 2, "message": "Cleared 2 message(s)."}`

```bash
# Verify empty
curl -s http://localhost:8000/api/v1/history \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

**Expected:** `{"messages": [], "count": 0}`

- [x] History has 2 messages after asking a question
- [x] Clear returns correct deleted count
- [x] History is empty after clearing

### 2.9 Document upload (admin only)

**First, make the test user an admin:**

1. Open **http://localhost:54323** (Supabase Studio)
2. Go to **Authentication → Users** → find `test@example.com`
3. Click the user → edit `raw_app_meta_data` → set to `{"provider": "email", "providers": ["email"], "is_admin": true}`
4. Save, then get a fresh token:

```bash
TOKEN=$(curl -s "http://127.0.0.1:54321/auth/v1/token?grant_type=password" \
  -H "apikey: $ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@test.local","password":"testpass123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

**Upload a test document:**

```bash
# Create a test document
printf "# Shelter Volunteer Handbook\n\nAll volunteers must check in at the front desk.\nFeeding schedule: 8am and 5pm daily.\nDogs must be walked twice per day." > /tmp/test-doc.md

# Upload (admin only, 201 on success)
curl -s -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/test-doc.md" | python3 -m json.tool
```

**Expected:** 201 response with `id` (UUID), `filename`, `title`, `chunks_created` (>0), `message`.

```bash
# List documents
curl -s http://localhost:8000/api/v1/documents \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

**Expected:** `count` of 1, document has `id`, `filename`, `title`, `file_type`, `file_size_bytes`, `is_indexed` (true), `created_at`.

```bash
# Save document ID for later tests
DOC_ID=<uuid from upload response>

# Ask a question that should hit the uploaded document
curl -s http://localhost:8000/api/v1/ask \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question":"What time is feeding?"}' | python3 -m json.tool
```

**Expected:** Answer references 8am and 5pm. `chunks_used` is non-empty with content from the document.

```bash
# Delete document (admin only)
curl -s -X DELETE http://localhost:8000/api/v1/documents/$DOC_ID \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

**Expected:** `{"message": "..."}`

- [x] Upload returns 201 with document metadata
- [x] Document appears in list with `is_indexed: true`
- [x] Ask returns answer grounded in uploaded content
- [x] Delete removes document

### 2.10 Non-admin cannot upload/delete

```bash
# Create a second non-admin user
curl -s http://127.0.0.1:54321/auth/v1/signup \
  -H "apikey: $ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"testpass123"}' > /dev/null

NON_ADMIN_TOKEN=$(curl -s "http://127.0.0.1:54321/auth/v1/token?grant_type=password" \
  -H "apikey: $ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"testpass123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Upload attempt → 403
curl -s -o /dev/null -w "%{http_code}" \
  -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer $NON_ADMIN_TOKEN" \
  -F "file=@/tmp/test-doc.md"
# Expected: 403

# Delete attempt → 403
curl -s -o /dev/null -w "%{http_code}" \
  -X DELETE http://localhost:8000/api/v1/documents/00000000-0000-0000-0000-000000000000 \
  -H "Authorization: Bearer $NON_ADMIN_TOKEN"
# Expected: 403
```

- [x] Non-admin upload returns 403
- [x] Non-admin delete returns 403

### 2.11 Input validation

```bash
# Empty question (min_length=1)
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/ask \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question":""}'
# Expected: 422

# Missing question field
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/ask \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
# Expected: 422

# Question too long (max_length=2000)
LONG_Q=$(python3 -c "print('x' * 2001)")
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/ask \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"question\":\"$LONG_Q\"}"
# Expected: 422
```

- [x] Empty question → 422
- [x] Missing field → 422
- [x] Oversized question (>2000 chars) → 422

### 2.12 CORS headers

```bash
# Allowed origin — should include access-control-allow-origin
curl -s -D - http://localhost:8000/health \
  -H "Origin: http://localhost:5173" -o /dev/null 2>&1 | grep -i access-control-allow-origin
# Expected: access-control-allow-origin: http://localhost:5173

# Disallowed origin — access-control-allow-origin must be ABSENT
# (access-control-allow-credentials may still appear — that's normal
# Starlette behavior and not a security issue without allow-origin)
curl -s -D - http://localhost:8000/health \
  -H "Origin: http://evil.com" -o /dev/null 2>&1 | grep -i access-control-allow-origin
# Expected: no output (empty)
```

- [x] `http://localhost:5173` gets `access-control-allow-origin` header
- [x] `http://evil.com` does NOT get `access-control-allow-origin` header

### 2.13 Observability

- [x] Backend terminal shows structured JSON logs with `request_id` fields
- [x] Jaeger UI at **http://localhost:16686** shows `retriever` service

> **Jaeger requires** `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317` in `.env`.
> Without it, traces fall through to console exporter (debug mode) or no-op.
> Docker compose exposes Jaeger's OTLP gRPC on port 4317, but the env var
> must be set explicitly — it is not in `.env.example` by default.
> After adding it, restart the backend and make a few requests before checking Jaeger.

---

## Phase 3: Frontend Automated Quality Gates

All commands run from `frontend/`.

### 3.1 Install dependencies

```bash
cd frontend
npm install
```

### 3.2 Type checking

```bash
npm run check
```

**Pass criteria:** Exit code 0.

> wrangler EPERM log warnings are harmless — ignore them.

### 3.3 Production build

```bash
npm run build
```

**Pass criteria:** Build completes without errors.

### 3.4 E2E tests

```bash
# Install Playwright browsers (first time only)
npx playwright install chromium

# Run E2E tests (auto-starts preview server on :4173)
npm run test:e2e
```

**Pass criteria:** All 9 tests pass:
- 3 home page tests (app bar, sign-in link, heading + tagline)
- 4 auth tests (chat redirect, admin redirect, login form render, empty submit validation)
- 1 chat redirect test
- 1 admin redirect test

---

## Phase 4: Frontend Manual Testing

**Requires:** Backend running on :8000, Supabase running, frontend dev server.

```bash
cd frontend
npm run dev
# Open http://localhost:5173
```

### 4.1 Landing page (unauthenticated)

- [x] Page loads at http://localhost:5173
- [x] App bar renders with "Retriever" title
- [x] "Sign In" link visible in navigation
- [x] Heading "Ask Retriever" and tagline display
- [x] Clicking "Sign In" navigates to `/login`

### 4.2 Route protection

- [x] Navigate to `/chat` → redirects to `/login`
- [x] Navigate to `/admin` → redirects to `/login`
- [x] Navigate to `/nonexistent` → error page displays

### 4.3 Login page

- [x] Email and password fields render
- [x] Empty submission shows validation feedback
- [x] Invalid credentials show error message
- [x] Valid credentials (`test@example.com` / `testpass123`) → redirects to `/chat`
- [x] After login, navigating to `/login` redirects to `/chat`

### 4.4 Chat page (authenticated)

- [x] Page loads with empty message area
- [x] Chat input textarea visible at bottom
- [x] Input has placeholder text
- [x] Can type a question
- [x] Enter sends the message (Shift+Enter for newline)
- [x] User message appears as bubble
- [x] Loading state shows while waiting for response
- [x] Assistant response appears with answer text
- [x] Confidence badge displays (high/medium/low with color)
- [x] Source citations expandable/collapsible (if chunks returned)
- [x] Multiple questions maintain conversation flow
- [x] Error state displays if backend is unreachable

### 4.5 Chat history

- [x] Refreshing the page preserves conversation history
- [x] Clear History button visible
- [x] Clicking Clear History shows confirmation
- [x] Confirming clears all messages
- [x] After clearing, chat area is empty

### 4.6 Admin page (admin user)

- [x] Page loads with document management interface
- [x] Document list shows uploaded documents (or empty state)
- [x] Upload button/area visible
- [x] Can select a file (.md or .txt)
- [x] Upload succeeds → document appears in list
- [x] Document list shows title, file type, indexed status, date
- [x] Desktop: renders as table; mobile: renders as cards
- [x] Delete button present on each document
- [x] Delete removes document from list

### 4.7 Admin page (non-admin user)

- [x] Navigate to `/admin` as non-admin → shows access denied or redirects to `/chat`

### 4.8 Logout

- [x] Logout button/link visible in navigation
- [x] Clicking logout redirects to landing or `/login`
- [x] After logout, `/chat` redirects to `/login`
- [x] After logout, `/admin` redirects to `/login`

### 4.9 Responsive design

- [x] Desktop width (1280px+): full layout
- [x] Tablet width (~768px): adapts navigation
- [x] Mobile width (~375px): chat messages readable, admin table → cards
- [x] Navigation adapts to viewport

### 4.10 Error handling

- [x] Stop the backend → frontend shows appropriate error on API calls
- [x] Restart backend → frontend recovers on next request
- [x] Browser Network tab: no failed requests during normal operation

---

## Phase 5: Integration Testing (Full Stack)

### 5.1 End-to-end RAG flow

1. Start everything (Supabase, Docker, backend, frontend)
2. Log in as admin
3. Upload a test document via Admin page
4. Switch to Chat page
5. Ask a question about the uploaded document
6. **Verify:** answer references content from the document
7. **Verify:** source citations show relevant chunks
8. **Verify:** confidence badge reflects match quality

### 5.2 Multi-user isolation

1. Create **User A** and **User B** in local Supabase
2. Log in as User A → ask questions → build history
3. Log out → log in as User B
4. **Verify:** User B has empty history (not User A's)
5. User B asks questions → builds own history
6. Log out → log in as User A
7. **Verify:** User A still has original history

### 5.3 Document lifecycle

1. Admin uploads document
2. Regular user asks question → gets answers from document
3. Admin deletes document
4. Regular user asks same question → should not find deleted content

### 5.4 Auth token behavior

1. Log in → note the time
2. JWT expiry is 3600s (1 hour) per Supabase config
3. Verify continued access works after token refresh
4. (Optional) Manually expire token → verify redirect to login

---

## Phase 6: CI/CD Verification

### 6.1 CI workflow dry-run

Run all checks that CI would run:

```bash
# Backend (from backend/)
cd backend
uv run ruff check src/ tests/ --fix
uv run ruff format src/ tests/ --check
uv run python -m mypy src/ --strict
uv run python -m pytest tests/ --cov=src/retriever --cov-fail-under=80

# Frontend (from frontend/)
cd ../frontend
npm run check
npm run build
npx playwright install chromium && npm run test:e2e
```

### 6.2 Docker build

```bash
cd backend

# Build the multi-stage Dockerfile
docker build -t retriever-backend:test .
```

**Pass criteria:** Build completes (Python 3.13-slim, uv install, non-root user).

```bash
# Verify container starts
docker run --rm -p 8001:8000 \
  -e DATABASE_URL=postgresql+asyncpg://postgres:postgres@host.docker.internal:5432/retriever \
  -e SUPABASE_URL=http://host.docker.internal:54321 \
  -e SUPABASE_ANON_KEY=test \
  -e OPENROUTER_API_KEY=test \
  -e OPENAI_API_KEY=test \
  retriever-backend:test &

sleep 10

curl -s http://localhost:8001/health | python3 -m json.tool
# DB may show "unavailable" if host.docker.internal doesn't resolve —
# the important thing is the container starts without crashing

# Clean up
docker stop $(docker ps -q --filter ancestor=retriever-backend:test)
```

- [x] `docker build` succeeds
- [x] Container starts and serves `/health`

### 6.3 Alembic migrations (reversibility)

```bash
cd backend

# Downgrade all 5 migrations
uv run alembic downgrade base

# Re-apply all
uv run alembic upgrade head
```

- [x] Downgrade to base completes without errors
- [x] Upgrade to head completes without errors

---

## Phase 7: Cleanup & Final Verification

### 7.1 Working tree clean

```bash
git status
```

- [x] No untracked files, no modifications (clean working tree)

### 7.2 No secrets committed

```bash
# Check for secret-looking files added in this branch
git log --all --diff-filter=A --name-only --pretty=format: main..HEAD \
  | sort -u | grep -iE '\.env$|secret|credential|\.key$'
# Expected: empty output

# Verify .env is gitignored
grep -i '\.env' .gitignore
```

- [x] No secret files in commit history
- [x] `.env` is in `.gitignore`

### 7.3 Documentation current

- [x] `CLAUDE.md` matches actual project structure
- [x] `CONTRIBUTING.md` setup instructions work end-to-end
- [x] `README.md` reflects new stack (not legacy monolith)
- [x] `docs/architecture.md` matches implementation

### 7.4 Legacy monolith removed

```bash
# Old monolith directories should NOT exist
ls src/ 2>/dev/null && echo "FAIL: legacy src/ still exists" || echo "PASS: legacy src/ removed"
```

- [x] No root-level `src/` directory

> Note: `.venv/` at root is the legacy virtualenv — verify it's gitignored but may still exist locally.

### 7.5 Stop infrastructure

```bash
docker compose -f docker-compose.test.yml down 2>/dev/null
docker compose down
supabase stop
```

---

## Summary Checklist

### Backend Automated Gates

| Gate | Command | Status |
|------|---------|--------|
| Lint | `ruff check` + `ruff format --check` | [ ] |
| Types | `python -m mypy --strict` | [ ] |
| Tests | `pytest` ≥80% coverage | [ ] |
| Security | `pip-audit` | [ ] |

### Backend Manual

| Test | Status |
|------|--------|
| `/health` returns healthy | [ ] |
| OpenAPI docs load | [ ] |
| Unauthenticated → 401 | [ ] |
| Authenticated → 200 | [ ] |
| RAG ask returns answer | [ ] |
| History save/get/clear | [ ] |
| Document upload (admin) | [ ] |
| Document delete (admin) | [ ] |
| Non-admin upload → 403 | [ ] |
| Non-admin delete → 403 | [ ] |
| Invalid input → 422 | [ ] |
| CORS allows/blocks correctly | [ ] |
| Structured JSON logs | [ ] |

### Frontend Automated Gates

| Gate | Command | Status |
|------|---------|--------|
| Types | `npm run check` | [ ] |
| Build | `npm run build` | [ ] |
| E2E (9 tests) | `npm run test:e2e` | [ ] |

### Frontend Manual

| Test | Status |
|------|--------|
| Landing page renders | [ ] |
| Route protection (redirects) | [ ] |
| Login flow | [ ] |
| Chat send/receive | [ ] |
| Chat history persistence + clear | [ ] |
| Admin upload/list/delete | [ ] |
| Non-admin admin access denied | [ ] |
| Logout flow | [ ] |
| Responsive (desktop/tablet/mobile) | [ ] |
| Error handling (backend down) | [ ] |

### Integration

| Test | Status |
|------|--------|
| Upload → ask → answer with citations | [ ] |
| Multi-user history isolation | [ ] |
| Document lifecycle (upload → query → delete → query) | [ ] |

### CI/CD & Cleanup

| Test | Status |
|------|--------|
| Docker build succeeds | [ ] |
| Container starts and serves health | [ ] |
| Migrations upgrade/downgrade clean | [ ] |
| Working tree clean | [ ] |
| No secrets committed | [ ] |
| Documentation current | [ ] |
| Legacy monolith removed | [ ] |

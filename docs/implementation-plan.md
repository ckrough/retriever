# GoodPuppy: Volunteer FAQ RAG Application

## Overview
AI-powered Q&A system for shelter volunteers, using RAG to answer questions from policy/procedure documents.

## Requirements Summary
- **Users**: Volunteers (self-service)
- **Documents**: 50-500 pages, Word/Markdown/text formats (stored in Git repo)
- **Updates**: Quarterly or less frequent
- **Interface**: Web application
- **LLM**: Anthropic Claude (via OpenRouter)
- **Auth**: Simple login (future: integrate with volunteer management system)
- **Deployment**: Cloud services acceptable (Railway or Render)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      DOCUMENT PIPELINE                          │
│  [Word/MD/Text] → [Loaders] → [Chunker] → [Embeddings] → [DB]  │
└─────────────────────────────────────────────────────────────────┘
                                                        ↓
┌─────────────────────────────────────────────────────────────────┐
│                        QUERY FLOW                               │
│  [User Question] → [Embed] → [Retrieve] → [Claude] → [Answer]  │
└─────────────────────────────────────────────────────────────────┘
                              ↑
┌─────────────────────────────────────────────────────────────────┐
│                      WEB APPLICATION                            │
│  [FastAPI Backend] ←→ [Simple Frontend] ←→ [Volunteer Browser] │
└─────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

### Backend (Python 3.11+)
| Component | Choice | Rationale |
|-----------|--------|-----------|
| Framework | FastAPI | Async, modern, good docs |
| LLM | OpenRouter (Claude via OpenAI-compatible API) | Multi-model access, simple pricing |
| LLM Abstraction | Protocol-based provider interface | Swap providers without code changes |
| Embeddings | OpenAI `text-embedding-3-small` | Cost-effective, high quality |
| Vector DB | Chroma | Simple, local-first, easy to start |
| Doc Loaders | `python-docx` + built-in | Lightweight loaders for Word, Markdown, text |
| Auth | `python-jose` + `passlib` | JWT tokens, bcrypt passwords |

### Frontend (MVP)
| Component | Choice | Rationale |
|-----------|--------|-----------|
| Approach | Server-rendered + HTMX | Simple, fast MVP, no JS build step |
| Styling | Tailwind CSS (CDN) | Quick, good defaults |
| Templates | Jinja2 | Built into FastAPI |

### Infrastructure
| Component | Choice | Rationale |
|-----------|--------|-----------|
| Hosting | Railway or Render | Simple deployment, free tiers |
| Vector DB | Chroma (persistent) | Embedded, no separate service |
| Database | SQLite | Simple, file-based, perfect for MVP |
| Document Storage | Git repository (`documents/`) | Version controlled, easy updates |
| Secrets | Environment variables | Standard practice |
| Observability | Sentry + structlog | Simple error tracking, structured logging |

---

## Architecture: Modular Monolith + Clean Architecture

**Why this approach (ADR-003):**
- Single deployment, low operational complexity
- Clear module boundaries enable future extraction to services
- API-first: frontend is just another API consumer
- Dependencies point inward (business logic doesn't know about FastAPI)

```
┌─────────────────────────────────────────────────────────────┐
│                      GoodPuppy (Monolith)                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Auth       │  │    RAG       │  │   Documents  │      │
│  │   Module     │  │   Module     │  │   Module     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                           ↓                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Shared Infrastructure                   │   │
│  │        (config, LLM providers, vector DB)           │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
                     REST/JSON API (v1)
                            │
              ┌─────────────┴─────────────┐
              ↓                           ↓
        Web Frontend              Future Integrations
```

---

## Project Structure

```
goodpuppy/
├── .devcontainer/
│   ├── devcontainer.json       # VS Code / Codespaces config
│   └── Dockerfile              # Dev environment
├── .github/
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md
│   │   └── feature_request.md
│   ├── PULL_REQUEST_TEMPLATE.md
│   ├── CONTRIBUTING.md
│   ├── CODE_OF_CONDUCT.md
│   └── workflows/
│       └── ci.yml              # Lint, test, type check
├── docs/
│   ├── architecture.md         # High-level system design
│   ├── decisions/              # Architecture Decision Records (ADRs)
│   │   ├── 000-template.md     # ADR template
│   │   ├── 001-tech-stack.md
│   │   ├── 002-llm-provider-strategy.md
│   │   ├── 003-system-architecture.md
│   │   ├── 004-vector-database.md
│   │   ├── 005-embedding-model.md
│   │   ├── 006-frontend-architecture.md
│   │   ├── 007-authentication-strategy.md
│   │   ├── 008-observability-stack.md
│   │   ├── 009-content-safety.md
│   │   ├── 010-resilience-patterns.md
│   │   └── 011-development-environment.md
│   └── guides/
│       ├── deployment.md       # How to deploy
│       └── adding-documents.md # How to add/update docs
├── src/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app entry point, mounts modules
│   ├── config.py               # Settings via pydantic-settings
│   │
│   ├── modules/                # Business modules (each self-contained)
│   │   ├── auth/               # === Authentication Module ===
│   │   │   ├── __init__.py
│   │   │   ├── routes.py       # POST /api/v1/auth/login, etc.
│   │   │   ├── services.py     # Business logic (login, register)
│   │   │   ├── repos.py        # User data access
│   │   │   ├── schemas.py      # Pydantic request/response
│   │   │   └── models.py       # User domain model
│   │   │
│   │   ├── rag/                # === RAG/Q&A Module ===
│   │   │   ├── __init__.py
│   │   │   ├── routes.py       # POST /api/v1/rag/ask
│   │   │   ├── services.py     # RAG orchestration (retrieve + generate)
│   │   │   ├── retriever.py    # Vector search logic
│   │   │   ├── generator.py    # Answer generation (uses LLMProvider)
│   │   │   └── schemas.py      # Question/Answer schemas
│   │   │
│   │   └── documents/          # === Document Management Module ===
│   │       ├── __init__.py
│   │       ├── routes.py       # GET /api/v1/documents, POST /admin/reindex
│   │       ├── services.py     # Indexing orchestration
│   │       ├── loaders.py      # Markdown, text, Word loaders (lightweight)
│   │       ├── chunker.py      # Text chunking logic
│   │       └── schemas.py      # Document metadata schemas
│   │
│   ├── infrastructure/         # Shared technical concerns
│   │   ├── __init__.py
│   │   ├── llm/                # LLM provider abstraction
│   │   │   ├── __init__.py
│   │   │   ├── base.py         # LLMProvider Protocol
│   │   │   ├── openrouter.py   # OpenRouter implementation
│   │   │   └── factory.py      # Provider factory
│   │   ├── vectordb/           # Vector database abstraction
│   │   │   ├── __init__.py
│   │   │   ├── base.py         # VectorStore Protocol
│   │   │   └── chroma.py       # Chroma implementation
│   │   ├── embeddings.py       # Embedding generation
│   │   └── database.py         # User DB (SQLite for MVP)
│   │
│   ├── api/                    # API layer concerns
│   │   ├── __init__.py
│   │   ├── router.py           # Mounts all module routes under /api/v1
│   │   ├── middleware.py       # Auth middleware, rate limiting
│   │   └── errors.py           # Standardized error responses
│   │
│   └── web/                    # Web frontend (server-rendered)
│       ├── __init__.py
│       ├── routes.py           # GET /, /login, /chat (HTML pages)
│       └── templates/
│           ├── base.html
│           ├── login.html
│           ├── chat.html
│           └── components/
│
├── scripts/
│   └── index_documents.py      # CLI to index docs
├── documents/                   # Source documents to index
├── data/                        # Chroma + SQLite persistent storage
├── tests/
│   ├── conftest.py
│   ├── modules/
│   │   ├── test_auth/
│   │   ├── test_rag/
│   │   └── test_documents/
│   └── infrastructure/
│       └── test_llm/
├── pyproject.toml
├── .env.example
└── README.md
```

---

## Implementation Phases (Agile Vertical Slices)

Each increment delivers a **working, visible feature** from backend to UI.

---

### Increment 1: Walking Skeleton 🦴
**Goal:** Prove the stack works end-to-end. Hardcoded everything.

**Deliverable:** A web page where you type a question and get a response.

```
[Browser] → [FastAPI] → [Hardcoded response] → [Browser]
```

**What you'll see:**
- Visit `http://localhost:8000`
- See a simple chat interface
- Type "Hello" → Get "Hello! I'm GoodPuppy, the volunteer assistant."

**Build:**
- [ ] Project setup (pyproject.toml, dev container)
- [ ] FastAPI app with single route
- [ ] Jinja2 template with Tailwind (chat UI)
- [ ] HTMX for form submission
- [ ] Hardcoded response (no LLM yet)
- [ ] Health endpoint `/health`

**Validates:** Dev environment, FastAPI, HTMX, Tailwind, deployment pipeline

---

### Increment 2: Real LLM Integration 🤖
**Goal:** Replace hardcoded response with actual Claude via OpenRouter.

**Deliverable:** Ask any question, get a real AI response (no RAG yet).

```
[Browser] → [FastAPI] → [OpenRouter/Claude] → [Browser]
```

**What you'll see:**
- Ask "What's the capital of France?" → Get actual Claude response
- See loading state while waiting
- See error message if API fails

**Build:**
- [ ] OpenRouter provider (Protocol-based)
- [ ] Environment config for API keys
- [ ] Loading spinner in UI
- [ ] Error handling + display
- [ ] Request timeouts (10s default)
- [ ] Rate limiting (10 requests/minute per session)
- [ ] Input validation (max 2000 chars, basic sanitization)

**Validates:** LLM integration, provider abstraction, error handling, basic protection

---

### Increment 3: Single Document RAG 📄
**Goal:** Load ONE document, answer questions from it.

**Deliverable:** Upload/index a document, ask questions about it.

```
[Document] → [Chunks] → [Embeddings] → [Chroma]
                                            ↓
[Question] → [Retrieve] → [Claude + Context] → [Answer]
```

**What you'll see:**
- Admin page: "Index document" button
- Index one shelter document
- Ask "Where do volunteers sign in?" → Answer from document
- See which chunks were used (debug view)

**Build:**
- [ ] Document loader (markdown/text first)
- [ ] Text chunker
- [ ] OpenAI embeddings
- [ ] Chroma vector store
- [ ] RAG pipeline (retrieve + generate)
- [ ] Admin page to trigger indexing
- [ ] Show retrieved chunks in response

**Validates:** Full RAG pipeline, chunking strategy, retrieval quality

---

### Increment 4: Multi-Document Support 📚
**Goal:** Index multiple documents, show sources in answers.

**Deliverable:** Index all shelter docs, answers cite their sources.

**What you'll see:**
- Index multiple documents
- Ask question → Answer with "Source: Volunteer Handbook, page 3"
- Admin view of all indexed documents

**Build:**
- [ ] Word document loader (.docx)
- [ ] Document metadata (title, source)
- [ ] Source citation in answers
- [ ] Document list in admin
- [ ] Re-index capability

**Validates:** Multi-document handling, citation accuracy

---

### Increment 5: Content Safety 🛡️
**Goal:** Filter inappropriate questions and responses.

**Deliverable:** Inappropriate content is blocked with friendly message.

**What you'll see:**
- Ask inappropriate question → "I can only help with volunteer questions"
- Off-topic question → "I don't have information about that"
- Logged for review (without storing harmful content)

**Build:**
- [ ] OpenAI Moderation API integration
- [ ] Input filtering
- [ ] Output filtering
- [ ] Fallback responses
- [ ] Safety logging

**Validates:** Content moderation, user experience for edge cases

---

### Increment 6: User Authentication 🔐
**Goal:** Volunteers must log in to use the app.

**Deliverable:** Login page, protected chat, user sessions.

**What you'll see:**
- Visit app → Redirected to login
- Log in with email/password
- Access chat interface
- Log out

**Build:**
- [ ] User model + SQLite
- [ ] Registration endpoint (admin creates users)
- [ ] Login page
- [ ] JWT session handling
- [ ] Protected routes
- [ ] Logout

**Validates:** Auth flow, session management

---

### Increment 7: Conversation History 💬
**Goal:** Remember conversation within a session.

**Deliverable:** Follow-up questions work, can see past Q&A.

**What you'll see:**
- Ask "Where do I sign in?"
- Follow up "What time does it open?" → Understands context
- Scroll up to see conversation history

**Build:**
- [ ] Conversation storage (session-based)
- [ ] Context window management
- [ ] Chat history UI
- [ ] Clear conversation button

**Validates:** Multi-turn conversations, context handling

---

### Increment 8: Q&A Audit Logging 📊
**Goal:** Track all questions and answers for improvement.

**Deliverable:** Admin can see what volunteers are asking.

**What you'll see:**
- Admin dashboard with recent Q&A
- Filter by date, user
- See unanswered/low-confidence questions
- Export for analysis

**Build:**
- [ ] Audit log table
- [ ] Log every Q&A with metadata
- [ ] Admin dashboard page
- [ ] Basic analytics (common questions)

**Validates:** Audit trail, data for improvement

---

### Increment 9: Observability & Monitoring 📈
**Goal:** Production-ready monitoring.

**Deliverable:** Error tracking, structured logs, cost visibility.

**What you'll see:**
- Sentry dashboard with errors and performance
- Structured logs queryable by request ID
- Cost tracking in admin dashboard
- Health check endpoints

**Build:**
- [ ] Sentry integration (errors + performance)
- [ ] structlog setup (JSON, request IDs)
- [ ] Cost tracking per request
- [ ] Health check endpoints (/health, /health/ready)
- [ ] External uptime monitoring (UptimeRobot)

**Validates:** Production readiness, debugging capability

---

### Increment 10: Feedback & Improvement 👍
**Goal:** Volunteers can rate answers.

**Deliverable:** Thumbs up/down on answers, feedback loop.

**What you'll see:**
- Each answer has 👍/👎 buttons
- Feedback stored for review
- Admin sees low-rated answers

**Build:**
- [ ] Feedback UI
- [ ] Feedback storage
- [ ] Admin feedback review
- [ ] Flag for document updates

**Validates:** Continuous improvement loop

---

### Increment 11: Mobile Polish 📱
**Goal:** Excellent mobile experience.

**Deliverable:** Fully responsive, touch-friendly on all devices.

**What you'll see:**
- Works great on phone, tablet, desktop
- Touch-friendly buttons
- Keyboard doesn't hide input
- Fast on slow connections

**Build:**
- [ ] Mobile testing & fixes
- [ ] Touch target optimization
- [ ] Offline-friendly error states
- [ ] Performance optimization

**Validates:** Real-world usability

---

### Increment 12: Production Deployment 🚀
**Goal:** Live on the internet, ready for volunteers.

**Deliverable:** Deployed app with documentation.

**What you'll see:**
- App running at `goodpuppy.example.org`
- SSL certificate
- Volunteers can actually use it

**Build:**
- [ ] Railway/Render deployment
- [ ] Environment configuration
- [ ] Domain + SSL
- [ ] Volunteer onboarding guide
- [ ] Admin documentation

**Validates:** Production deployment, real users

---

## Increment Dependencies

```
1. Walking Skeleton
        ↓
2. LLM Integration
        ↓
3. Single Document RAG ←─── Core MVP
        ↓
4. Multi-Document
        ↓
    ┌───┴───┐
    ↓       ↓
5. Safety  6. Auth
    ↓       ↓
    └───┬───┘
        ↓
7. Conversation History
        ↓
8. Audit Logging
        ↓
    ┌───┴───┐
    ↓       ↓
9. Observability  10. Feedback
    ↓       ↓
    └───┬───┘
        ↓
11. Mobile Polish
        ↓
12. Production
```

**MVP = Increments 1-4** (functional Q&A from documents)

---

## Key Design Decisions

### Chunking Strategy
- **Method**: Recursive character text splitter
- **Chunk size**: ~500 tokens (roughly 2000 chars)
- **Overlap**: 100 tokens (400 chars)
- **Rationale**: Balances context preservation with retrieval precision

### Retrieval Strategy
- **Top-K**: Retrieve top 5 chunks
- **Similarity threshold**: 0.7 minimum score
- **Re-ranking**: Not for MVP (add if quality issues arise)

### Prompt Design
```
You are a helpful assistant for [Shelter Name] volunteers.
Answer questions based ONLY on the provided context.
If the answer is not in the context, say "I don't have information about that in our documents."
Always cite which document the information comes from.

Context:
{retrieved_chunks}

Question: {user_question}
```

### LLM Provider Abstraction (ADR-002)
```python
# src/llm/base.py
from typing import Protocol

class LLMProvider(Protocol):
    """Abstract interface for LLM providers - swap implementations without changing RAG code."""

    async def complete(
        self,
        system_prompt: str,
        user_message: str,
        model: str | None = None
    ) -> str:
        """Generate a completion. Returns the response text."""
        ...

# src/llm/openrouter.py
class OpenRouterProvider:
    """OpenRouter implementation using OpenAI-compatible API."""

    def __init__(self, api_key: str, default_model: str = "anthropic/claude-sonnet-4"):
        self.client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key
        )
        self.default_model = default_model

    async def complete(self, system_prompt: str, user_message: str, model: str | None = None) -> str:
        response = await self.client.chat.completions.create(
            model=model or self.default_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
        )
        return response.choices[0].message.content
```

**Future providers** (add when needed):
- `src/llm/anthropic.py` - Direct Anthropic SDK
- `src/llm/litellm.py` - LiteLLM wrapper
- `src/llm/local.py` - Ollama/local models

**Swapping providers**: Change `LLM_PROVIDER` env var, factory returns correct implementation.

### Auth Design (Future-Proofed)
- Simple email/password for MVP
- User model includes `external_id` field for future integration
- Auth logic isolated in `auth/` module for easy swap-out

---

## Dependencies

```toml
[project]
dependencies = [
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "openai>=1.12.0",           # For OpenRouter (compatible API) + embeddings
    "chromadb>=0.4.22",
    "python-docx>=1.1.0",           # Word doc parsing (lightweight)
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
    "pydantic>=2.6.0",
    "pydantic-settings>=2.1.0",
    "python-multipart>=0.0.9",   # Form handling
    "jinja2>=3.1.3",
    "httpx>=0.26.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
    "ruff>=0.2.0",
    "mypy>=1.8.0",
]
```

---

## Operational Concerns

### 1. Development in Dev Containers

```
.devcontainer/
├── devcontainer.json       # VS Code / GitHub Codespaces config
├── Dockerfile              # Development environment image
└── docker-compose.yml      # Local services (if needed)
```

**Configuration:**
```json
{
  "name": "GoodPuppy Dev",
  "build": { "dockerfile": "Dockerfile" },
  "features": {
    "ghcr.io/devcontainers/features/python:1": { "version": "3.12" }
  },
  "postCreateCommand": "pip install -e '.[dev]'",
  "customizations": {
    "vscode": {
      "extensions": ["ms-python.python", "charliermarsh.ruff"]
    }
  },
  "forwardPorts": [8000]
}
```

**Benefits:** Consistent environment across developers, easy onboarding, works with VS Code and GitHub Codespaces.

---

### 2. Tracing and Troubleshooting

**Approach:** Simplified observability stack for MVP - Sentry for errors, structlog for structured logging.

```
src/infrastructure/
├── observability/
│   ├── __init__.py
│   ├── logging.py          # structlog setup
│   └── sentry.py           # Sentry initialization
```

**Stack:**
| Component | Choice | Rationale |
|-----------|--------|-----------|
| Error Tracking | Sentry | One-click setup, free tier, automatic context |
| Logging | structlog | Structured JSON logs, easy to query |
| Metrics | Basic timing in logs | Good enough for MVP, upgrade later if needed |

**Logs capture:**
- Request IDs for correlation
- Token counts, latencies per component
- Retrieved chunk IDs for debugging relevance
- Structured JSON format for easy parsing

**Future upgrade path:** Add OpenTelemetry when you need distributed tracing across services.

---

### 3. Logging and Auditing Q&A

**Audit Log Table:**
```sql
CREATE TABLE qa_audit_log (
    id UUID PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    user_id UUID REFERENCES users(id),
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    retrieved_chunks JSONB,      -- [{doc_id, chunk_id, score}]
    model_used VARCHAR(100),
    token_count_input INT,
    token_count_output INT,
    latency_ms INT,
    feedback_rating INT          -- Optional user feedback
);
```

**Implementation:**
```
src/modules/rag/
├── audit.py                # Audit logging service
```

**Retention:** Configurable (default 90 days), with option to anonymize after N days.

---

### 4. Safety and Risk Filtering

**Layered Approach:**

| Layer | Tool | Purpose |
|-------|------|---------|
| Input filter | OpenAI Moderation API | Fast, low-latency pre-check |
| Prompt guardrails | System prompt constraints | Scope limitation |
| Output filter | Same moderation API | Verify response safety |

**Implementation:**
```
src/infrastructure/
├── safety/
│   ├── __init__.py
│   ├── moderation.py       # Content filtering
│   └── guardrails.py       # Input/output validation
```

**Example flow:**
```python
async def ask(question: str) -> Answer:
    # 1. Check input safety
    if not await safety.is_safe(question):
        return Answer(text="I can only answer questions about volunteering.", flagged=True)

    # 2. RAG pipeline
    answer = await rag.generate(question)

    # 3. Check output safety (belt + suspenders)
    if not await safety.is_safe(answer.text):
        return Answer(text="I couldn't generate a safe response.", flagged=True)

    return answer
```

**Considerations for volunteer context:**
- Block inappropriate content (harassment, explicit)
- Detect off-topic questions (not about shelter/volunteering)
- Log flagged content for review (without storing harmful text)

---

### 5. Cost Tracking and Management

**Tracked Costs:**
| Service | Metric | Typical Cost |
|---------|--------|--------------|
| OpenRouter (Claude) | Tokens in/out | ~$3/1M input, ~$15/1M output |
| OpenAI Embeddings | Tokens | ~$0.02/1M tokens |
| Moderation API | Requests | Free |

**Implementation:**
```
src/infrastructure/
├── costs/
│   ├── __init__.py
│   ├── tracker.py          # Per-request cost calculation
│   └── alerts.py           # Budget threshold alerts
```

**Features:**
- Per-request cost logged in audit table
- Daily/weekly cost aggregation
- Configurable budget alerts (email when >80% of monthly budget)
- Cost dashboard in admin UI

**Cost table:**
```sql
CREATE TABLE cost_tracking (
    id UUID PRIMARY KEY,
    date DATE NOT NULL,
    service VARCHAR(50),        -- 'openrouter', 'openai_embeddings'
    tokens_input BIGINT,
    tokens_output BIGINT,
    cost_usd DECIMAL(10, 6),
    request_count INT
);
```

---

### 6. Performance Monitoring

**Metrics collected:**
| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| P50 response time | <2s | >3s |
| P95 response time | <5s | >8s |
| RAG retrieval time | <500ms | >1s |
| LLM generation time | <3s | >5s |
| Error rate | <1% | >5% |

**Implementation:**
- Timing logged via structlog (queryable in log aggregator)
- Sentry performance monitoring (automatic)
- Simple dashboards via Sentry UI

**Future upgrade:** Add Prometheus/Grafana if you need real-time alerting or complex dashboards.

---

### 7. Availability Monitoring

**Health Endpoints:**
```
GET /health          → Basic liveness (app running)
GET /health/ready    → Readiness (dependencies OK)
GET /health/detailed → Full status (for debugging)
```

**Readiness checks:**
- Vector DB (Chroma) accessible
- LLM provider (OpenRouter) reachable
- Database connection valid

**External monitoring:**
- Uptime service (UptimeRobot free tier, or Checkly)
- Alert on downtime via email/Slack

---

### 8. Resilience: Timeouts and Retries

**Approach:** Start simple with timeouts and retries. Add circuit breakers only after observing real failure patterns.

**Libraries:** `tenacity` (retries) + `httpx` timeouts

**Applied to:**
| Dependency | Timeout | Retry Strategy |
|------------|---------|----------------|
| OpenRouter API | 30s | 2 retries, exponential backoff |
| OpenAI Embeddings | 10s | 2 retries, exponential backoff |
| Chroma | 5s | 1 retry (local, should be fast) |

**Implementation:**
```python
from tenacity import retry, stop_after_attempt, wait_exponential
import httpx

# Simple timeout + retry (no circuit breaker for MVP)
@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, max=5))
async def call_openrouter(messages: list) -> str:
    async with httpx.AsyncClient(timeout=30.0) as client:
        ...
```

**Fallback behavior:**
- On timeout/error: Return friendly "Service temporarily unavailable, please try again" message
- Log all failures for pattern analysis

**Future upgrade:** Add circuit breakers (`aiobreaker`) if you see cascading failures or need to fail fast.

---

### 9. Responsive UI Design

**Approach:** Mobile-first responsive design with Tailwind CSS

**Breakpoints:**
| Device | Width | Layout |
|--------|-------|--------|
| Mobile | <640px | Single column, full-width chat |
| Tablet | 640-1024px | Centered container, larger text |
| Desktop | >1024px | Max-width container, sidebar optional |

**Implementation:**
```html
<!-- Mobile-first, scales up -->
<div class="w-full md:max-w-2xl lg:max-w-4xl mx-auto px-4">
  <div class="flex flex-col h-screen">
    <header class="py-4">...</header>
    <main class="flex-1 overflow-y-auto">
      <!-- Chat messages -->
    </main>
    <footer class="py-4">
      <!-- Input form -->
    </footer>
  </div>
</div>
```

**Features:**
- Touch-friendly buttons (min 44px tap targets)
- Readable text on all sizes (16px base)
- Input field stays visible when keyboard opens (mobile)
- Progressive enhancement (works without JS, better with)

---

## Updated Project Structure

```
src/
├── infrastructure/
│   ├── llm/                    # LLM providers (existing)
│   ├── vectordb/               # Vector DB (existing)
│   ├── observability/          # Logging and error tracking
│   │   ├── __init__.py
│   │   ├── logging.py          # structlog setup
│   │   └── sentry.py           # Sentry initialization
│   ├── safety/                 # Content moderation
│   │   ├── __init__.py
│   │   ├── moderation.py
│   │   └── guardrails.py
│   ├── costs/                  # Cost tracking
│   │   ├── __init__.py
│   │   ├── tracker.py
│   │   └── alerts.py
│   └── rate_limit.py           # Simple rate limiting
```

---

## Updated Dependencies

Add to `pyproject.toml`:
```toml
# Observability (simplified for MVP)
"sentry-sdk[fastapi]>=1.40.0",  # Error tracking with FastAPI integration
"structlog>=24.1.0",             # Structured logging

# Resilience
"tenacity>=8.2.0",               # Retries with backoff

# Rate limiting
"slowapi>=0.1.9",                # Rate limiting for FastAPI
```

---

## Architecture Decision Records (ADRs)

Each ADR follows the format: **Status**, **Context**, **Decision**, **Consequences**.

### ADR-000: Template
Standard ADR template for consistency.

### ADR-001: Tech Stack Selection
- **Decision:** FastAPI, Python 3.12+, Pydantic 2.x, uvicorn
- **Context:** Need modern async framework for API + web
- **Alternatives:** Django (heavier, less async-native), Flask (less structured)
- **Consequences:** Fast development, good typing support, excellent docs

### ADR-002: LLM Provider Strategy
- **Decision:** OpenRouter initially, with Protocol-based abstraction for swapping
- **Context:** Want Claude, but need flexibility for cost/model changes
- **Alternatives:** Direct Anthropic SDK (locked in), LiteLLM (production issues)
- **Consequences:** Easy model switching, slight abstraction overhead

### ADR-003: System Architecture
- **Decision:** Modular monolith with clean architecture principles
- **Context:** Small team, need API for integrations, want maintainability
- **Alternatives:** Microservices (overkill), flat monolith (hard to maintain)
- **Consequences:** Simple deployment, clear boundaries, extraction path exists

### ADR-004: Vector Database
- **Decision:** Chroma (embedded/persistent mode)
- **Context:** 50-500 pages of docs, quarterly updates, simple ops preferred
- **Alternatives:** Pinecone (managed, costs), pgvector (need Postgres), Qdrant
- **Consequences:** Zero external services, simple backup, may need to migrate at scale

### ADR-005: Embedding Model
- **Decision:** OpenAI text-embedding-3-small
- **Context:** Need quality semantic search, cost-effective
- **Alternatives:** text-embedding-3-large (2x cost), open-source (lower quality)
- **Consequences:** ~$0.02/1M tokens, 1536 dimensions, vendor dependency

### ADR-006: Frontend Architecture
- **Decision:** Server-rendered with Jinja2 + HTMX + Tailwind CSS
- **Context:** MVP needs simple chat UI, mobile-responsive
- **Alternatives:** React SPA (complex build), plain HTML (poor UX)
- **Consequences:** No JS build step, fast initial load, limited interactivity

### ADR-007: Authentication Strategy
- **Decision:** Simple JWT auth now, designed for future integration
- **Context:** Need login for volunteers, will integrate with existing system later
- **Alternatives:** OAuth immediately (complex), no auth (security risk)
- **Consequences:** Quick MVP, `external_id` field ready for integration

### ADR-008: Observability Stack
- **Decision:** Sentry (errors) + structlog (structured logging) for MVP
- **Context:** Need error tracking and debugging capability without complex setup
- **Alternatives:** OpenTelemetry + OpenLLMetry (powerful but complex), custom logging only (limited)
- **Consequences:** Quick setup, free tier sufficient, upgrade path to OpenTelemetry exists

### ADR-009: Content Safety
- **Decision:** OpenAI Moderation API for input + output filtering
- **Context:** Volunteers may ask inappropriate questions, need guardrails
- **Alternatives:** NeMo Guardrails (complex), Llama Guard (self-hosted)
- **Consequences:** Free, fast, may over-filter edge cases

### ADR-010: Resilience Patterns
- **Decision:** Timeouts + tenacity (retries) for MVP; add circuit breakers later if needed
- **Context:** External API dependencies (OpenRouter, OpenAI) can fail
- **Alternatives:** Full circuit breaker setup (premature optimization), no resilience (fragile)
- **Consequences:** Simple, predictable behavior; upgrade path exists when failure patterns emerge

### ADR-012: Rate Limiting
- **Decision:** slowapi for per-session rate limiting (10 requests/minute)
- **Context:** Prevent abuse and runaway costs from excessive requests
- **Alternatives:** Custom implementation (reinventing wheel), no limits (cost risk)
- **Consequences:** Simple protection, configurable limits, minimal overhead

### ADR-011: Development Environment
- **Decision:** Dev Containers for VS Code / GitHub Codespaces
- **Context:** Want consistent dev environment, easy onboarding
- **Alternatives:** Local setup docs only (inconsistent), Docker Compose (heavier)
- **Consequences:** Works in VS Code + Codespaces, Python version locked

---

## Decisions Made

- **App name**: GoodPuppy
- **Test documents**: User will provide
- **LLM approach**: OpenRouter with swappable provider abstraction (ADR-002)
- **Architecture**: Modular monolith with clean architecture (ADR-003)
- **API design**: REST/JSON, versioned (/api/v1), frontend is an API consumer
- **Database**: SQLite (file-based, simple for MVP)
- **Document storage**: Git repository (`documents/` folder, version controlled)
- **Development**: Dev containers for consistent environment
- **Observability**: Sentry (errors) + structlog (logging) - simplified for MVP (ADR-008)
- **Safety**: OpenAI Moderation API (input + output filtering)
- **Resilience**: Timeouts + tenacity (retries) - circuit breakers deferred (ADR-010)
- **Rate limiting**: slowapi (10 req/min per session) (ADR-012)
- **Input validation**: Max 2000 chars, basic sanitization
- **UI**: Mobile-first responsive with Tailwind CSS
- **Document parsing**: Lightweight (python-docx + built-in) - no PDF parsing needed
- **Git workflow**: GitHub Flow (main + feature branches, squash merge)
- **Code quality**: ruff + mypy --strict + 80% test coverage
- **PR process**: 1 approval required, CI must pass

## Development Standards (for CLAUDE.md)

### Overview
Standards for distributed, open-source development with contributors across time zones.

### Git Workflow: GitHub Flow
```
main (protected) ← feature branches via PR

1. Create feature branch from main
2. Make changes, commit with conventional messages
3. Open PR, request review
4. 1 approval required + CI passes
5. Squash merge to main
6. Delete feature branch
```

**Branch naming:**
```
feature/add-user-auth
fix/chat-input-validation
docs/update-readme
refactor/simplify-rag-pipeline
```

**Commit messages (Conventional Commits):**
```
feat: add volunteer login functionality
fix: resolve chat timeout on slow connections
docs: add API endpoint documentation
test: add coverage for RAG retrieval
refactor: extract LLM provider interface
chore: update dependencies
```

### Code Quality Standards

**Required for all code:**
```yaml
# Enforced by CI
- ruff check (linting)
- ruff format (formatting)
- mypy --strict (type checking)
- pytest --cov=src --cov-fail-under=80 (80% coverage minimum)
- pip-audit (security vulnerabilities)
```

**Type hints:** Required on all function signatures
```python
# ✅ Good
async def ask_question(question: str, user_id: UUID) -> Answer:
    ...

# ❌ Bad - missing types
async def ask_question(question, user_id):
    ...
```

**Docstrings:** Required for public APIs (Google style)
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

### Testing Standards

**Coverage:** 80% minimum for new code

**Test naming:** `test_<function>_<scenario>_<expected>`
```python
def test_ask_question_with_valid_input_returns_answer():
    ...

def test_ask_question_with_empty_context_returns_fallback():
    ...

def test_moderation_with_unsafe_content_raises_blocked_error():
    ...
```

**Test categories:**
```
tests/
├── unit/           # Fast, isolated tests (mock dependencies)
├── integration/    # Tests with real dependencies (DB, APIs)
└── e2e/            # Full workflow tests
```

**Required tests:**
- Unit tests for all business logic
- Integration tests for API endpoints
- Regression tests for bug fixes

### Documentation Requirements

**Required documentation:**
| What | Where | When to Update |
|------|-------|----------------|
| API endpoints | Docstrings + OpenAPI | When endpoints change |
| Architecture | `docs/architecture.md` | Major changes |
| Decisions | `docs/decisions/NNN-*.md` | New ADR for significant choices |
| Setup | `README.md` | When setup changes |
| Config | `.env.example` | New env vars |

**ADR format:**
```markdown
# NNN: Title

## Status
Proposed | Accepted | Deprecated | Superseded by NNN

## Context
What is the issue that we're seeing that is motivating this decision?

## Decision
What is the change that we're proposing and/or doing?

## Consequences
What becomes easier or more difficult because of this change?
```

### PR Requirements

**Before opening PR:**
- [ ] All tests pass locally
- [ ] New code has tests (80% coverage)
- [ ] Types check with mypy
- [ ] Linting passes (ruff)
- [ ] Documentation updated if needed
- [ ] ADR created for significant decisions

**PR template:**
```markdown
## Summary
Brief description of changes.

## Type
- [ ] Feature
- [ ] Bug fix
- [ ] Refactor
- [ ] Documentation
- [ ] Tests

## Testing
How was this tested?

## Checklist
- [ ] Tests pass
- [ ] Types check
- [ ] Docs updated
- [ ] ADR added (if significant decision)
```

**Review process:**
- 1 approval required
- CI must pass
- Squash merge (clean history)

### Security Standards

**Never commit:**
- API keys, secrets, passwords
- `.env` files (use `.env.example`)
- Credentials of any kind

**Required:**
- `pip-audit` in CI (vulnerability scanning)
- Secrets in environment variables only
- Input validation on all endpoints
- Content moderation on user input

### Communication

**Where discussions happen:**
| Topic | Location |
|-------|----------|
| Bugs & features | GitHub Issues |
| Code review | GitHub PRs |
| Architecture decisions | ADRs + GitHub Discussions |
| Quick questions | GitHub Discussions |

---

## Files to Create for Standards

```
.github/
├── ISSUE_TEMPLATE/
│   ├── bug_report.md
│   └── feature_request.md
├── PULL_REQUEST_TEMPLATE.md
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
└── workflows/
    └── ci.yml              # Linting, testing, type checking
```

**CLAUDE.md additions:**
- Code style section (ruff, mypy)
- Testing requirements
- PR process
- Commit message format
- Branch naming convention

---

## Open Questions

1. **Existing volunteer system**: What system do volunteers currently use? (for future auth integration)

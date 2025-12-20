# Retriever Architecture

AI-powered Q&A system for shelter volunteers, using RAG to answer questions from policy/procedure documents.

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      DOCUMENT PIPELINE                          │
│  [Word/MD/Text] → [Loaders] → [Chunker] → [Embeddings] → [DB]   │
└─────────────────────────────────────────────────────────────────┘
                                                        ↓
┌─────────────────────────────────────────────────────────────────┐
│                        QUERY FLOW                               │
│  [User Question] → [Embed] → [Retrieve] → [Claude] → [Answer]   │
└─────────────────────────────────────────────────────────────────┘
                              ↑
┌─────────────────────────────────────────────────────────────────┐
│                      WEB APPLICATION                            │
│  [FastAPI Backend] ←→ [Simple Frontend] ←→ [Volunteer Browser]  │
└─────────────────────────────────────────────────────────────────┘
```

## Architecture Style: Modular Monolith

Single deployable unit with clean module boundaries. See [ADR-003](decisions/003-system-architecture.md).

**Why this approach:**
- Single deployment, low operational complexity
- Clear module boundaries enable future extraction to services
- API-first: frontend is just another API consumer
- Dependencies point inward (business logic doesn't know about FastAPI)

```
┌────────────────────────────────────────────────────────────┐
│                      Retriever (Monolith)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Auth       │  │    RAG       │  │   Documents  │      │
│  │   Module     │  │   Module     │  │   Module     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                           ↓                                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Shared Infrastructure                  │   │
│  │        (config, LLM providers, vector DB)           │   │
│  └─────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────┘
                            │
                     REST/JSON API (v1)
                            │
              ┌─────────────┴─────────────┐
              ↓                           ↓
        Web Frontend              Future Integrations
```

## Tech Stack

### Backend (Python 3.12+)

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

## Project Structure

```
retriever/
├── src/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app entry point
│   ├── config.py               # Settings via pydantic-settings
│   │
│   ├── modules/                # Business modules (each self-contained)
│   │   ├── auth/               # Authentication
│   │   │   ├── __init__.py
│   │   │   ├── routes.py       # POST /api/v1/auth/login, etc.
│   │   │   ├── services.py     # Business logic
│   │   │   ├── repos.py        # User data access
│   │   │   ├── schemas.py      # Pydantic request/response
│   │   │   └── models.py       # User domain model
│   │   │
│   │   ├── rag/                # RAG/Q&A Module
│   │   │   ├── __init__.py
│   │   │   ├── routes.py       # POST /api/v1/rag/ask
│   │   │   ├── services.py     # RAG orchestration
│   │   │   ├── retriever.py    # Vector search logic
│   │   │   ├── generator.py    # Answer generation
│   │   │   └── schemas.py      # Question/Answer schemas
│   │   │
│   │   └── documents/          # Document Management
│   │       ├── __init__.py
│   │       ├── routes.py       # GET /api/v1/documents
│   │       ├── services.py     # Indexing orchestration
│   │       ├── loaders.py      # File loaders
│   │       ├── chunker.py      # Text chunking
│   │       └── schemas.py      # Document schemas
│   │
│   ├── infrastructure/         # Shared technical concerns
│   │   ├── llm/                # LLM providers
│   │   │   ├── base.py         # LLMProvider Protocol
│   │   │   ├── openrouter.py   # OpenRouter implementation
│   │   │   ├── resilient.py    # Fallback chain
│   │   │   └── factory.py      # Provider factory
│   │   ├── vectordb/           # Vector DB
│   │   │   ├── base.py         # VectorStore Protocol
│   │   │   └── chroma.py       # Chroma implementation
│   │   ├── cache/              # Semantic caching
│   │   │   └── semantic_cache.py
│   │   ├── safety/             # Content safety
│   │   │   ├── moderation.py   # OpenAI Moderation API
│   │   │   ├── guardrails.py   # Input/output validation
│   │   │   ├── hallucination.py
│   │   │   └── prompt_injection.py
│   │   ├── observability/      # Logging and errors
│   │   │   ├── logging.py      # structlog setup
│   │   │   └── sentry.py       # Sentry initialization
│   │   ├── costs/              # Cost tracking
│   │   │   ├── tracker.py
│   │   │   └── alerts.py
│   │   ├── embeddings.py
│   │   ├── database.py
│   │   └── rate_limit.py
│   │
│   ├── api/                    # API layer
│   │   ├── router.py           # Mount module routes
│   │   ├── middleware.py       # Auth, rate limiting
│   │   └── errors.py           # Error responses
│   │
│   └── web/                    # Server-rendered frontend
│       ├── routes.py           # HTML pages
│       └── templates/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   ├── rag_evaluation/         # RAG quality tests
│   │   ├── golden_dataset.py
│   │   └── test_rag_quality.py
│   ├── modules/
│   └── infrastructure/
│
├── docs/                       # You are here
├── scripts/
├── documents/                  # Source documents to index
├── data/                       # Chroma + SQLite storage
├── pyproject.toml
├── .env.example
└── README.md
```

## Key Design Patterns

### LLM Provider Abstraction

Protocol-based interface for swappable LLM providers:

```python
class LLMProvider(Protocol):
    async def complete(
        self,
        system_prompt: str,
        user_message: str,
        model: str | None = None
    ) -> str: ...
```

See [ADR-002](decisions/002-llm-provider-strategy.md).

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

## Related Documents

- [Implementation Roadmap](implementation-plan.md)
- [Development Standards](development-standards.md)
- [Architecture Decision Records](decisions/)

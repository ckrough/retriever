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
┌────────────────────────────────────────────────────────────┐
│                      GoodPuppy (Monolith)                  │
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
│   │   │   ├── resilient.py    # Fallback chain provider
│   │   │   └── factory.py      # Provider factory
│   │   ├── vectordb/           # Vector database abstraction
│   │   │   ├── __init__.py
│   │   │   ├── base.py         # VectorStore Protocol
│   │   │   └── chroma.py       # Chroma implementation
│   │   ├── cache/              # Semantic caching
│   │   │   ├── __init__.py
│   │   │   └── semantic_cache.py  # Answer cache by question similarity
│   │   ├── safety/             # Content safety (expanded)
│   │   │   ├── __init__.py
│   │   │   ├── moderation.py   # OpenAI Moderation API
│   │   │   ├── guardrails.py   # Input/output validation
│   │   │   ├── hallucination.py    # Hallucination detection
│   │   │   └── prompt_injection.py # Injection attack detection
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
│   ├── unit/                    # Fast, isolated unit tests
│   ├── integration/             # Tests with real dependencies
│   ├── e2e/                     # Full workflow tests
│   ├── rag_evaluation/          # RAG quality tests
│   │   ├── golden_dataset.py    # Q&A pairs for quality testing
│   │   └── test_rag_quality.py  # Retrieval & answer accuracy tests
│   ├── modules/
│   │   ├── test_auth/
│   │   ├── test_rag/
│   │   └── test_documents/
│   └── infrastructure/
│       ├── test_llm/
│       ├── test_cache/
│       └── test_safety/
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
- [ ] Request timeouts (30s for LLM calls)
- [ ] Circuit breaker for LLM calls (fail fast after 5 failures)
- [ ] Rate limiting (10 requests/minute per session)
- [ ] Input validation (max 2000 chars, basic sanitization)

**Validates:** LLM integration, provider abstraction, error handling, resilience

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

### Increment 5: RAG Quality Hardening 🎯
**Goal:** Production-grade RAG quality: caching, evaluation, hybrid retrieval.

**Deliverable:** Faster responses, measurable quality, better retrieval.

**What you'll see:**
- Repeated questions return instantly (~50ms vs ~3s)
- RAG quality tests run in CI with pass/fail
- Answers cite sources more accurately

**Build:**
- [ ] Semantic caching (cache by question similarity)
- [ ] Golden Q&A dataset (30+ examples from real docs)
- [ ] RAG quality tests (retrieval accuracy, answer accuracy)
- [ ] Hybrid retrieval (semantic + BM25 keyword search)
- [ ] Reranking integration (Cohere or RRF)
- [ ] Cache invalidation on document reindex
- [ ] Quality metrics logging

**Validates:** Cache effectiveness, retrieval quality improvement, regression detection

---

### Increment 6: Content Safety 🛡️
**Goal:** Filter inappropriate content, detect attacks, prevent hallucinations.

**Deliverable:** Safe, accurate answers with attack prevention.

**What you'll see:**
- Ask inappropriate question → "I can only help with volunteer questions"
- Prompt injection attempt → Blocked and logged
- Answers verified against source documents
- Low-confidence answers flagged for review

**Build:**
- [ ] OpenAI Moderation API integration
- [ ] Input/output filtering
- [ ] Prompt injection detection (pattern-based)
- [ ] Hallucination detection (claim verification)
- [ ] Confidence scoring for answers
- [ ] Fallback responses for low-confidence
- [ ] Safety logging (without storing harmful content)
- [ ] Model fallback chain (Sonnet → Haiku)

**Validates:** Content moderation, attack prevention, answer accuracy

---

### Increment 7: User Authentication 🔐
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

### Increment 8: Conversation History 💬
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

### Increment 9: Q&A Audit Logging 📊
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

### Increment 10: Observability & Monitoring 📈
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

### Increment 11: Feedback & Improvement 👍
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

### Increment 12: Mobile Polish 📱
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

### Increment 13: Production Deployment 🚀
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
3. Single Document RAG ←─── Core MVP (functional Q&A)
        ↓
4. Multi-Document
        ↓
5. RAG Quality Hardening ←─── Quality MVP (caching, evaluation, hybrid search)
        ↓
    ┌───┴───┐
    ↓       ↓
6. Safety  7. Auth
    ↓       ↓
    └───┬───┘
        ↓
8. Conversation History
        ↓
9. Audit Logging
        ↓
    ┌────┴────┐
    ↓         ↓
10. Observability  11. Feedback
    ↓         ↓
    └────┬────┘
         ↓
12. Mobile Polish
         ↓
13. Production
```

**Core MVP = Increments 1-4** (functional Q&A from documents)
**Quality MVP = Increments 1-5** (production-grade RAG with caching and evaluation)

---

## Key Design Decisions

### Chunking Strategy
- **Method**: Structure-aware recursive text splitter
- **Chunk size**: ~375 tokens (1500 chars) - leaves room for prompt context
- **Overlap**: 200 tokens (800 chars) - larger overlap preserves context across boundaries
- **Separator hierarchy**: Section headers → Paragraphs → Sentences → Words
- **Metadata preserved**: Source document, section title, chunk type (list/paragraph/table)
- **Rationale**: Document structure matters - splitting mid-sentence or mid-list degrades retrieval quality

**Implementation approach:**
```python
# Respect document structure when chunking
separators = [
    "\n## ",     # H2 headers (section breaks)
    "\n### ",    # H3 headers (subsections)
    "\n\n",      # Paragraphs
    "\n",        # Lines
    ". ",        # Sentences
    " ",         # Words (last resort)
]

# Each chunk includes metadata:
{
    "chunk_id": "doc_123_chunk_5",
    "source_doc": "Volunteer Handbook",
    "section": "Check-in Procedures",
    "chunk_type": "paragraph" | "list" | "table",
    "page_number": 12  # if available
}
```

### Retrieval Strategy
- **Approach**: Hybrid search (semantic + keyword) with reranking
- **Over-retrieve**: Fetch top 10 chunks initially
- **Final top-K**: Return top 5 after reranking
- **Similarity threshold**: Validated on domain data (not arbitrary 0.7)
- **Re-ranking**: Cohere rerank API (~$0.001/query) or Reciprocal Rank Fusion (free)

**Why hybrid search matters:**
- Semantic search misses exact keyword matches ("check-in" vs "sign in")
- Keyword search misses semantic similarity ("entrance" vs "front desk")
- Combining both improves recall significantly

**Implementation approach:**
```python
async def retrieve(self, query: str, top_k: int = 5) -> list[Chunk]:
    # 1. Semantic search (over-retrieve)
    semantic_chunks = await self.vector_store.similarity_search(query, k=top_k * 2)

    # 2. Keyword search (BM25 on chunk text)
    keyword_chunks = await self.keyword_search(query, k=top_k)

    # 3. Merge and deduplicate
    merged = self._merge_results(semantic_chunks, keyword_chunks)

    # 4. Rerank (Cohere API or RRF)
    reranked = await self._rerank(query, merged, top_k)

    return reranked[:top_k]
```

### Prompt Design

**System prompt:**
```
You are GoodPuppy, an AI assistant for {shelter_name} volunteers.

Your job is to answer questions using ONLY the provided policy documents.

RULES:
1. If the answer is in the documents, provide a clear, concise response
2. If the answer is NOT in the documents, say: "I don't have information about that in our volunteer documentation."
3. If you're uncertain, say: "Based on the available information, [answer], but I recommend confirming with your volunteer coordinator."
4. ALWAYS cite your sources in this format: (Source: [Document Name], Section [X])
5. Keep answers under 150 words unless the question requires detail
6. If multiple documents have conflicting information, mention both and flag the discrepancy
```

**User prompt template:**
```
Here are relevant excerpts from our volunteer documentation:

[1] Source: Volunteer Handbook, Section: Check-in Procedures
{chunk_1_text}

---

[2] Source: Safety Guidelines, Section: Emergency Protocols
{chunk_2_text}

---

Question: {user_question}

Remember: Only answer based on the excerpts above. Cite your sources.
```

**Key improvements:**
- Explicit citation format for consistency
- Uncertainty handling ("I recommend confirming...")
- Conflict detection for contradictory documents
- Length constraint to prevent rambling

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

## RAG Quality Hardening

Production RAG systems require quality controls beyond basic retrieval + generation. This section covers critical hardening measures.

### 1. Semantic Caching (ADR-013)

**Problem:** Volunteers ask similar questions repeatedly. Without caching:
- Unnecessary LLM costs
- 3-second responses instead of 50ms
- Higher load on OpenRouter

**Solution:** Cache answers based on semantic similarity of questions.

```python
# src/infrastructure/cache/semantic_cache.py
class SemanticCache:
    """Cache answers for semantically similar questions."""

    def __init__(self, similarity_threshold: float = 0.95):
        self.threshold = similarity_threshold

    async def get(self, question: str) -> Answer | None:
        """Return cached answer if similar question was asked."""
        question_embedding = await embed(question)
        results = self.cache_collection.query(
            query_embeddings=[question_embedding],
            n_results=1
        )

        if results and results['distances'][0][0] < (1 - self.threshold):
            return Answer.parse_raw(results['documents'][0][0])
        return None

    async def set(self, question: str, answer: Answer, ttl_hours: int = 24) -> None:
        """Store answer in cache (only for high-confidence answers)."""
        # Only cache high-confidence answers
        if answer.confidence != "high":
            return
        # ... store in cache collection
```

**Expected impact:**
- ~40% cache hit rate for common questions
- 60x faster responses for cached queries (3s → 50ms)
- ~40% reduction in LLM costs

**Cache invalidation:** Clear cache when documents are reindexed.

---

### 2. Hallucination Detection (ADR-014)

**Problem:** LLM may generate information not present in source documents. This is the #1 risk in RAG systems.

**Solution:** Validate that answer claims are grounded in retrieved chunks.

```python
# src/infrastructure/safety/hallucination_detector.py
class HallucinationDetector:
    """Detect when LLM generates information not in source chunks."""

    async def check(self, answer: str, chunks: list[Chunk]) -> bool:
        """
        Returns True if answer is grounded, False if hallucinated.

        Approach:
        1. Extract factual claims from answer
        2. Check if each claim is supported by chunks
        3. Flag if >20% of claims are unsupported
        """
        claims = self._extract_claims(answer)

        supported_count = 0
        for claim in claims:
            if await self._is_supported(claim, chunks):
                supported_count += 1

        support_ratio = supported_count / len(claims) if claims else 1.0
        return support_ratio >= 0.8  # 80% of claims must be supported
```

**When hallucination detected:**
```python
if not await hallucination_detector.check(answer_text, chunks):
    logger.warning("Hallucination detected", answer=answer_text)
    return Answer(
        text="I don't have enough information to answer that confidently.",
        confidence="low",
        needs_human_review=True
    )
```

**Cost:** Adds ~100ms latency, ~$0.0001/query. Worth it for accuracy.

---

### 3. RAG Evaluation Dataset

**Problem:** Without a test dataset, you can't measure RAG quality or detect regressions.

**Solution:** Create a golden Q&A dataset from actual documents.

```python
# tests/rag_evaluation/golden_dataset.py
GOLDEN_QA_PAIRS = [
    {
        "question": "Where do volunteers sign in?",
        "expected_answer_contains": "front desk",
        "expected_source": "Volunteer Handbook",
        "category": "orientation"
    },
    {
        "question": "What do I do if a dog bites me?",
        "expected_answer_contains": ["immediately", "notify staff"],
        "expected_source": "Safety Procedures",
        "category": "safety"
    },
    # ... 30-50 examples covering key topics
]

# tests/rag_evaluation/test_rag_quality.py
@pytest.mark.asyncio
async def test_retrieval_accuracy():
    """Correct source document should be in top-3 chunks."""
    rag = RAGService()
    correct = 0

    for qa in GOLDEN_QA_PAIRS:
        chunks = await rag.retriever.retrieve(qa["question"])
        sources = [c.source_doc for c in chunks[:3]]
        if qa["expected_source"] in sources:
            correct += 1

    accuracy = correct / len(GOLDEN_QA_PAIRS)
    assert accuracy >= 0.80, f"Retrieval accuracy {accuracy:.2%} below 80% threshold"
```

**Metrics to track:**

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Retrieval accuracy | >80% | Correct doc in top-3 |
| Answer accuracy | >85% | Expected keywords in answer |
| Citation accuracy | >90% | Correct source cited |
| Hallucination rate | <5% | Unsupported claims |

---

### 4. Prompt Injection Defense (ADR-015)

**Problem:** Users may attempt "Ignore previous instructions..." attacks.

**Solution:** Pattern-based detection for known injection attempts.

```python
# src/infrastructure/safety/prompt_injection.py
import re

INJECTION_PATTERNS = [
    r"ignore (previous|above|all) (instructions|rules)",
    r"disregard (all|your) (instructions|rules|guidelines)",
    r"new (instructions|task|role)",
    r"you are now",
    r"system prompt",
    r"reveal (your|the) (instructions|prompt|api)",
]

def is_prompt_injection(question: str) -> bool:
    """Detect common prompt injection patterns."""
    question_lower = question.lower()
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, question_lower):
            return True
    return False

# In RAG service
async def ask(self, question: str) -> Answer:
    if is_prompt_injection(question):
        logger.warning("Prompt injection attempt", question=question[:100])
        return Answer(
            text="I can only answer questions about volunteer policies and procedures.",
            flagged=True
        )
```

---

### 5. Answer Quality Controls

**Problem:** Need confidence scoring and graceful degradation.

**Solution:** Add confidence assessment and fallback behavior.

```python
# src/modules/rag/generator.py
class AnswerGenerator:
    async def generate(self, question: str, chunks: list[Chunk]) -> Answer:
        # 1. Check if chunks are relevant enough
        relevance_scores = [c.score for c in chunks]
        if not chunks or max(relevance_scores) < 0.6:
            return Answer(
                text="I don't have relevant information about that in our documentation.",
                confidence="low",
                sources=[]
            )

        # 2. Generate answer
        raw_answer = await self.llm.complete(system_prompt, user_prompt)

        # 3. Self-assessment for confidence
        confidence = await self._assess_confidence(question, raw_answer, chunks)

        # 4. Check for hallucinations (high-value answers only)
        if confidence == "high":
            is_grounded = await self.hallucination_detector.check(raw_answer, chunks)
            if not is_grounded:
                confidence = "low"

        return Answer(
            text=raw_answer,
            confidence=confidence,
            sources=[c.source_doc for c in chunks],
            needs_human_review=(confidence == "low")
        )
```

---

### 6. Model Fallback

**Problem:** If Claude is unavailable, entire system fails.

**Solution:** Fallback to cheaper/faster model, then graceful degradation.

```python
# src/infrastructure/llm/resilient_provider.py
class ResilientLLMProvider:
    """LLM provider with fallback chain."""

    def __init__(self):
        self.primary = OpenRouterProvider(model="anthropic/claude-sonnet-4")
        self.fallback = OpenRouterProvider(model="anthropic/claude-haiku-4")

    async def complete(self, system: str, user: str) -> str:
        try:
            return await self.primary.complete(system, user)
        except (TimeoutError, RateLimitError) as e:
            logger.warning("Primary model failed, trying fallback", error=str(e))
            return await self.fallback.complete(system, user)
        except Exception as e:
            logger.error("All LLM providers failed", error=str(e))
            raise LLMProviderError("Unable to generate answer") from e
```

**Graceful degradation:** If all LLMs fail, return retrieved chunks directly:
```python
except LLMProviderError:
    return Answer(
        text="I found these relevant sections:\n\n" + "\n\n".join(c.text for c in chunks),
        confidence="low",
        is_fallback=True
    )
```

---

### 7. RAG-Specific Monitoring

**What to log for every request:**
```python
{
    "request_id": "abc123",
    "question": "Where do I sign in?",
    "retrieval": {
        "chunks_found": 5,
        "top_score": 0.89,
        "latency_ms": 45,
        "sources": ["Volunteer Handbook"]
    },
    "generation": {
        "model": "claude-sonnet-4",
        "input_tokens": 2450,
        "output_tokens": 145,
        "latency_ms": 2300,
        "cost_usd": 0.0087
    },
    "answer": {
        "confidence": "high",
        "has_citations": true,
        "hallucination_check": "passed"
    },
    "cache": {
        "hit": false
    }
}
```

**Alerts to configure:**
- Average retrieval score drops below 0.7 for 1 hour
- Hallucination rate exceeds 10%
- Less than 50% of answers have citations
- Cache hit rate drops significantly (may indicate doc changes)

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
    "cohere>=5.0.0",             # Reranking for hybrid search
    "rank-bm25>=0.2.2",          # BM25 keyword search
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

### 8. Resilience: Timeouts, Retries, and Circuit Breakers

**Approach:** Timeouts + retries + circuit breakers for LLM calls. Circuit breakers prevent cascading failures when external APIs are degraded.

**Libraries:** `tenacity` (retries) + `httpx` (timeouts) + `aiobreaker` (circuit breaker)

**Applied to:**
| Dependency | Timeout | Retry Strategy | Circuit Breaker |
|------------|---------|----------------|-----------------|
| OpenRouter API | 30s | 2 retries, exponential backoff | Open after 5 failures, 60s reset |
| OpenAI Embeddings | 10s | 2 retries, exponential backoff | Open after 5 failures, 60s reset |
| Chroma | 5s | 1 retry (local, should be fast) | None (local) |

**Implementation:**
```python
from tenacity import retry, stop_after_attempt, wait_exponential
from aiobreaker import CircuitBreaker
import httpx

# Circuit breaker for LLM calls
llm_breaker = CircuitBreaker(
    fail_max=5,           # Open after 5 consecutive failures
    timeout_duration=60,  # Stay open for 60 seconds
)

@llm_breaker
@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, max=5))
async def call_openrouter(messages: list) -> str:
    async with httpx.AsyncClient(timeout=30.0) as client:
        ...
```

**Fallback behavior:**
- On timeout/error: Return friendly "Service temporarily unavailable, please try again" message
- On circuit open: Fail immediately (don't wait for timeout)
- Log all failures for pattern analysis

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
│   ├── llm/                    # LLM providers
│   │   ├── base.py             # LLMProvider Protocol
│   │   ├── openrouter.py       # OpenRouter implementation
│   │   ├── resilient.py        # Fallback chain (Sonnet → Haiku)
│   │   └── factory.py          # Provider factory
│   ├── vectordb/               # Vector DB
│   ├── cache/                  # Semantic caching
│   │   └── semantic_cache.py   # Answer cache by question similarity
│   ├── observability/          # Logging and error tracking
│   │   ├── logging.py          # structlog setup
│   │   └── sentry.py           # Sentry initialization
│   ├── safety/                 # Content safety (expanded)
│   │   ├── moderation.py       # OpenAI Moderation API
│   │   ├── guardrails.py       # Input/output validation
│   │   ├── hallucination.py    # Hallucination detection
│   │   └── prompt_injection.py # Injection attack detection
│   ├── costs/                  # Cost tracking
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
"aiobreaker>=1.2.0",             # Circuit breaker for async calls

# Rate limiting
"slowapi>=0.1.9",                # Rate limiting for FastAPI

# RAG Quality (from architect review)
"cohere>=5.0.0",                 # Reranking for hybrid search
"rank-bm25>=0.2.2",              # BM25 keyword search
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
- **Decision:** Timeouts + tenacity (retries) + aiobreaker (circuit breaker) for LLM calls
- **Context:** External API dependencies (OpenRouter, OpenAI) can fail; cascading failures are unacceptable
- **Alternatives:** No circuit breaker (cascading failures), complex resilience (overkill)
- **Consequences:** Fail-fast behavior prevents thread pool exhaustion; simple aiobreaker config

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

### ADR-013: Semantic Caching
- **Decision:** Cache RAG answers using semantic similarity matching
- **Context:** Volunteers ask similar questions; caching reduces costs and latency
- **Alternatives:** Exact-match cache (misses similar questions), no cache (expensive)
- **Consequences:** ~40% cost reduction, 60x faster cached responses, need cache invalidation on doc updates

### ADR-014: Hallucination Detection
- **Decision:** Validate LLM answers are grounded in retrieved chunks before returning
- **Context:** RAG systems can hallucinate; volunteers need accurate information
- **Alternatives:** Trust LLM output (risky), manual review all answers (doesn't scale)
- **Consequences:** Better accuracy, ~100ms added latency, some false positives possible

### ADR-015: Prompt Injection Defense
- **Decision:** Pattern-based detection for common prompt injection attacks
- **Context:** Public-facing LLM systems are targets for injection attacks
- **Alternatives:** No defense (vulnerable), complex NLP detection (overkill for MVP)
- **Consequences:** Blocks common attacks, may need updates as attack patterns evolve

### ADR-016: Hybrid Retrieval with Reranking
- **Decision:** Combine semantic + keyword search, then rerank results
- **Context:** Pure semantic search misses exact keyword matches; pure keyword misses meaning
- **Alternatives:** Semantic only (current), keyword only (poor semantic understanding)
- **Consequences:** Better retrieval accuracy, small cost for reranking (~$0.001/query)

---

## Decisions Made

### Core Architecture
- **App name**: GoodPuppy
- **Test documents**: User will provide
- **LLM approach**: OpenRouter with swappable provider abstraction (ADR-002)
- **Architecture**: Modular monolith with clean architecture (ADR-003)
- **API design**: REST/JSON, versioned (/api/v1), frontend is an API consumer
- **Database**: SQLite (file-based, simple for MVP)
- **Document storage**: Git repository (`documents/` folder, version controlled)

### RAG Quality (from LLM Architect Review)
- **Chunking**: Structure-aware (respects headers, paragraphs) with 1500 char chunks, 800 char overlap
- **Retrieval**: Hybrid search (semantic + BM25 keyword) with Cohere reranking (ADR-016)
- **Caching**: Semantic cache for similar questions (~40% cost reduction) (ADR-013)
- **Evaluation**: Golden Q&A dataset (30+ examples) with CI quality tests
- **Hallucination detection**: Verify answer claims against source chunks (ADR-014)
- **Prompt injection defense**: Pattern-based detection (ADR-015)
- **Model fallback**: Sonnet → Haiku chain for resilience
- **Answer confidence**: Self-assessment with low-confidence flagging

### Safety & Resilience
- **Content moderation**: OpenAI Moderation API (input + output filtering)
- **Resilience**: Timeouts + tenacity (retries) + aiobreaker (circuit breaker) (ADR-010)
- **Rate limiting**: slowapi (10 req/min per session) (ADR-012)
- **Input validation**: Max 2000 chars, basic sanitization

### Development & Operations
- **Development**: Dev containers for consistent environment
- **Observability**: Sentry (errors) + structlog (logging) - simplified for MVP (ADR-008)
- **UI**: Mobile-first responsive with Tailwind CSS
- **Document parsing**: Lightweight (python-docx + built-in) - no PDF parsing needed

### Code Quality & Process
- **Git workflow**: GitHub Flow (main + feature branches, squash merge)
- **Code quality**: ruff + mypy --strict + 80% test coverage
- **PR process**: 1 approval required, CI must pass

### Deferred (Post-Validation)
- **Operational excellence**: Backups, DR runbooks, advanced monitoring - see "Future: Production Hardening"
- **LLMOps maturity**: A/B testing, model benchmarking, prompt versioning
- **Philosophy**: Validate product-market fit first, then harden for operations

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

## Future: Production Hardening (Post-Validation)

> **Philosophy:** First validate the product is useful and wanted, then harden for operations.
> These items are captured from AI engineering review but intentionally deferred until
> the app has proven its value with real users.

### When to Implement

Trigger production hardening when:
- App has been used by real volunteers for 2+ weeks
- Positive feedback confirms product-market fit
- Decision made to invest in long-term operation

### Deferred Operational Items

**Data Durability (Priority: High when scaling)**
- [ ] Automated SQLite backup to cloud storage (daily)
- [ ] Chroma vector DB backup after each reindex
- [ ] Backup verification tests (can we actually restore?)
- [ ] Define RPO/RTO targets (suggested: RPO 24h, RTO 1h)

**Disaster Recovery**
- [ ] Document runbooks for common failure scenarios
- [ ] Secondary hosting provider config (backup to Railway if on Render, or vice versa)
- [ ] Incident response procedures

**Advanced Observability**
- [ ] Distributed tracing (OpenTelemetry) for RAG pipeline debugging
- [ ] Rich metrics dashboard (token trends, embedding costs, cache effectiveness)
- [ ] User journey tracking (session analytics)
- [ ] Alerting runbooks with specific thresholds and escalation paths
- [ ] Anomaly detection for quality degradation

**LLMOps Maturity**
- [ ] A/B testing infrastructure for models and prompts
- [ ] Model performance benchmarking on golden dataset
- [ ] Prompt version control (prompts in config, not code)
- [ ] Smart model routing (Haiku for simple questions, Sonnet for complex)
- [ ] Cost attribution by user/session

**Data Pipeline Hardening**
- [ ] Pipeline failure handling (partial success, corrupted docs)
- [ ] Data versioning (track embedding model version per chunk)
- [ ] Incremental indexing (only reindex changed documents)
- [ ] Large document streaming (handle 200+ page docs)

**Security & Compliance**
- [ ] API key rotation strategy (multiple keys, automatic rotation)
- [ ] Data privacy procedures (GDPR/CCPA if applicable)
- [ ] Complete admin audit logging (who deleted/changed what)
- [ ] Data retention and anonymization policies

**Deployment Maturity**
- [ ] Blue-green or canary deployment strategy
- [ ] Automatic rollback on high error rates
- [ ] Resource limits and scaling thresholds
- [ ] Database connection pool tuning

### Why Defer These?

1. **Validation first**: No point hardening an app nobody uses
2. **YAGNI**: Some operational concerns won't materialize at small scale
3. **Learning**: Real usage reveals actual pain points vs. hypothetical ones
4. **Focus**: Early phases should focus on core RAG quality, not ops

### Estimated Effort

Once triggered, production hardening is approximately:
- **High priority items** (backups, DR docs): 1-2 weeks
- **Full operational maturity**: 4-6 weeks additional

---

## Open Questions

1. **Existing volunteer system**: What system do volunteers currently use? (for future auth integration)

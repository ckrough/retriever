# Retriever: Implementation Plan

AI-powered Q&A system for shelter volunteers, using RAG to answer questions from policy/procedure documents.

## Quick Links

| Document | Description |
|----------|-------------|
| [Architecture](architecture.md) | System design, tech stack, project structure |
| [Increments](increments.md) | Implementation roadmap (13 increments) |
| [Development Standards](development-standards.md) | Code quality, Git workflow, PR process |
| [ADRs](decisions/) | Architecture Decision Records |
| [Deployment Guide](guides/deployment.md) | How to deploy to Railway/Render |
| [Adding Documents](guides/adding-documents.md) | Managing policy documents |

---

## Requirements Summary

- **Users**: Volunteers (self-service)
- **Documents**: 50-500 pages, Word/Markdown/text formats (stored in Git repo)
- **Updates**: Quarterly or less frequent
- **Interface**: Web application (mobile-friendly)
- **LLM**: Anthropic Claude (via OpenRouter)
- **Auth**: Simple login (future: integrate with volunteer management system)
- **Deployment**: Cloud services (Railway or Render)

---

## Milestones

| Milestone | Increments | What You Get |
|-----------|------------|--------------|
| **Core MVP** | 1-4 | Functional Q&A from documents |
| **Quality MVP** | 1-5 | + Caching, evaluation, hybrid retrieval |
| **Full MVP** | 1-7 | + Safety, authentication |
| **Production** | 1-13 | Complete system with monitoring, feedback |

---

## Key Design Decisions

### RAG Pipeline
- **Chunking**: Structure-aware (1500 chars, 800 overlap, respects headers)
- **Retrieval**: Hybrid search (semantic + BM25) with reranking
- **Caching**: Semantic cache for similar questions (~40% cost reduction)
- **Quality**: Hallucination detection, confidence scoring, golden Q&A dataset

### Architecture
- **Style**: Modular monolith with clean architecture
- **LLM**: OpenRouter with Protocol-based abstraction for swapping
- **Vector DB**: Chroma (embedded, persistent)
- **Database**: SQLite (users, audit logs)

### Safety & Resilience
- **Content moderation**: OpenAI Moderation API
- **Prompt injection**: Pattern-based detection
- **Resilience**: Timeouts + retries + circuit breakers
- **Rate limiting**: 10 req/min per session

See [ADRs](decisions/) for detailed rationale on each decision.

---

## Dependencies

```toml
[project]
dependencies = [
    # Web framework
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "jinja2>=3.1.3",
    "python-multipart>=0.0.9",

    # LLM & Embeddings
    "openai>=1.12.0",
    "httpx>=0.26.0",

    # Vector DB & RAG
    "chromadb>=0.4.22",
    "cohere>=5.0.0",
    "rank-bm25>=0.2.2",

    # Document processing
    "python-docx>=1.1.0",

    # Auth
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",

    # Validation & Config
    "pydantic>=2.6.0",
    "pydantic-settings>=2.1.0",

    # Observability
    "sentry-sdk[fastapi]>=1.40.0",
    "structlog>=24.1.0",

    # Resilience
    "tenacity>=8.2.0",
    "aiobreaker>=1.2.0",
    "slowapi>=0.1.9",
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

### Observability
- **Error tracking**: Sentry (free tier)
- **Logging**: structlog (JSON, request IDs)
- **Metrics**: Basic timing in logs, Sentry performance

### Cost Tracking
- Per-request cost logged in audit table
- Budget alerts at 80% threshold
- Cost dashboard in admin UI

### Health Checks
```
GET /health          → Basic liveness
GET /health/ready    → Dependencies OK
```

### Resilience
| Dependency | Timeout | Circuit Breaker |
|------------|---------|-----------------|
| OpenRouter | 30s | Open after 5 failures |
| OpenAI Embeddings | 10s | Open after 5 failures |
| Chroma | 5s | None (local) |

---

## Future: Production Hardening (Post-Validation)

> **Philosophy:** First validate the product is useful and wanted, then harden for operations.

These items are captured from engineering review but intentionally deferred until the app has proven its value with real users.

### When to Implement

Trigger production hardening when:
- App has been used by real volunteers for 2+ weeks
- Positive feedback confirms product-market fit
- Decision made to invest in long-term operation

### Deferred Operational Items

**Data Durability**
- [ ] Automated SQLite backup to cloud storage (daily)
- [ ] Chroma vector DB backup after each reindex
- [ ] Backup verification tests
- [ ] Define RPO/RTO targets (suggested: RPO 24h, RTO 1h)

**Disaster Recovery**
- [ ] Document runbooks for common failure scenarios
- [ ] Secondary hosting provider config
- [ ] Incident response procedures

**Advanced Observability**
- [ ] Distributed tracing (OpenTelemetry)
- [ ] Rich metrics dashboard
- [ ] User journey tracking
- [ ] Anomaly detection

**LLMOps Maturity**
- [ ] A/B testing infrastructure for models and prompts
- [ ] Model performance benchmarking
- [ ] Prompt version control
- [ ] Smart model routing (Haiku for simple, Sonnet for complex)
- [ ] Cost attribution by user/session

**Data Pipeline Hardening**
- [ ] Pipeline failure handling (partial success, corrupted docs)
- [ ] Data versioning (track embedding model version per chunk)
- [ ] Incremental indexing (only reindex changed documents)
- [ ] Large document streaming

**Security & Compliance**
- [ ] API key rotation strategy
- [ ] Data privacy procedures (GDPR/CCPA if applicable)
- [ ] Complete admin audit logging
- [ ] Data retention and anonymization policies

**Deployment Maturity**
- [ ] Blue-green or canary deployment
- [ ] Automatic rollback on high error rates
- [ ] Resource limits and scaling thresholds

### Estimated Effort

Once triggered:
- **High priority items** (backups, DR docs): 1-2 weeks
- **Full operational maturity**: 4-6 weeks additional

---

## Open Questions

1. **Existing volunteer system**: What system do volunteers currently use? (for future auth integration)

<p align="center">
  <img src="assets/logo.png" alt="Retriever Logo" width="200" height="200">
</p>

<p align="center">
  <strong>AI-powered Q&A for your organization's documents</strong>
</p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#configuration">Configuration</a> •
  <a href="#deployment">Deployment</a> •
  <a href="#documentation">Documentation</a>
</p>

---

Retriever is an AI-powered question-answering system that helps users find information in your organization's policy and procedure documents. Upload your documents, and Retriever uses RAG (Retrieval-Augmented Generation) to provide accurate, sourced answers.

Retriever can be adapted for any organization with documentation that users need to search.

## Features

- **Natural Language Q&A** — Ask questions in plain English and get accurate answers with source citations
- **Multi-Document Support** — Index multiple markdown and text documents
- **Source Citations** — Every answer includes clickable citations to the original documents
- **Conversation History** — Continue conversations with context from previous questions
- **Hybrid Search** — Combines semantic understanding with keyword matching for better retrieval
- **Content Safety** — Built-in moderation and hallucination detection
- **User Authentication** — Secure login system with JWT tokens
- **Semantic Caching** — Faster responses for similar questions
- **Rate Limiting** — Prevent abuse with configurable request limits

## Quick Start

### Prerequisites

- Python 3.13+ with [uv](https://docs.astral.sh/uv/)
- Node.js 22+
- Docker
- [Supabase CLI](https://supabase.com/docs/guides/cli)
- API keys: [OpenRouter](https://openrouter.ai/keys) (LLM) and [OpenAI](https://platform.openai.com/api-keys) (embeddings/moderation)

### Get Running

```bash
git clone https://github.com/your-org/retriever.git
cd retriever
cp .env.example .env
# Edit .env with your API keys

supabase start                    # Auth + Supabase services
docker compose up -d              # pgvector postgres + jaeger

cd backend && uv sync --extra dev
uv run alembic upgrade head
uv run uvicorn retriever.main:app --reload --port 8000

# In a separate terminal:
cd frontend && npm install && npm run dev
```

Backend API: [http://localhost:8000/docs](http://localhost:8000/docs) | Frontend: [http://localhost:5173](http://localhost:5173)

See [CONTRIBUTING.md](CONTRIBUTING.md) for full development setup, quality checks, and workflow.

## Usage

### Web Interface

1. **Login** — Create an account or log in at `/login`
2. **Ask Questions** — Type your question in the chat interface
3. **View Sources** — Click citation cards to see the original document text
4. **Continue Conversations** — Ask follow-up questions with context preserved

### API

Retriever exposes a REST API for programmatic access:

```bash
# Ask a question
curl -X POST http://localhost:8000/api/v1/rag/ask \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"question": "What is the check-in procedure?"}'
```

API documentation is available at `/docs` (OpenAPI/Swagger).

## Configuration

See `.env.example` for all configuration options. Required API keys:

| Variable | Description |
|----------|-------------|
| `OPENROUTER_API_KEY` | LLM provider API key |
| `OPENAI_API_KEY` | Embeddings and moderation API key |

Auth is handled by Supabase (local via `supabase start`, production via Supabase project). See [CONTRIBUTING.md](CONTRIBUTING.md) for full environment setup.

### Document Preparation

For best results:

- Use **markdown format** with clear headings (`#`, `##`, `###`)
- Keep sections focused on single topics
- Use descriptive headings that match how users ask questions
- Include relevant keywords naturally in the text

## Deployment

- **Backend:** Cloud Run via `gcloud run deploy --source ./backend`
- **Frontend:** Cloudflare Pages
- **Database:** Supabase (managed Postgres + pgvector)

### Production Checklist

- [ ] Set `DEBUG=false`
- [ ] Configure Supabase project with RLS policies
- [ ] Set up Cloudflare AI Gateway for LLM routing
- [ ] Configure OpenTelemetry (GCP Cloud Trace or OTLP endpoint)
- [ ] Enable Langfuse for LLM observability (optional)
- [ ] HTTPS handled by Cloud Run / Cloudflare Pages

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DOCUMENT PIPELINE                         │
│  [Markdown/Text] → [Chunker] → [Embeddings] → [pgvector]     │
└─────────────────────────────────────────────────────────────┘
                                                    ↓
┌─────────────────────────────────────────────────────────────┐
│                      QUERY FLOW                              │
│  [Question] → [Hybrid Search] → [Rerank] → [LLM] → [Answer]  │
└─────────────────────────────────────────────────────────────┘
```

**Tech Stack:**
- **Backend:** Python 3.13+, FastAPI, SQLAlchemy 2.0 async, Pydantic 2.x
- **LLM:** OpenRouter via Cloudflare AI Gateway
- **Vector DB:** Supabase Postgres + pgvector (HNSW cosine + GIN full-text)
- **Frontend:** SvelteKit + Svelte 5 runes + Skeleton UI v4
- **Auth:** Supabase Auth / JWKS
- **Observability:** structlog + OpenTelemetry + Langfuse
- **Deploy:** Cloud Run (backend), Cloudflare Pages (frontend)

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for full setup and quality check commands.

## Documentation

- [Architecture Overview](docs/architecture.md)
- [Development Standards](docs/development-standards.md)
- [Implementation Roadmap](docs/increments.md)
- [Deployment Guide](docs/guides/deployment.md)
- [Adding Documents](docs/guides/adding-documents.md)

## License

MIT

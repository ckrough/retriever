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

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- API keys for:
  - [OpenRouter](https://openrouter.ai/keys) (for LLM access)
  - [OpenAI](https://platform.openai.com/api-keys) (for embeddings and moderation — free tier available)

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/retriever.git
cd retriever

# Install dependencies
uv sync --extra dev

# Copy environment template
cp .env.example .env
```

### Configuration

Edit `.env` with your API keys:

```bash
# Required
OPENROUTER_API_KEY=your-openrouter-key
OPENAI_API_KEY=your-openai-key
JWT_SECRET_KEY=generate-a-random-secret-key

# Optional (defaults work for local development)
LLM_MODEL=anthropic/claude-sonnet-4
DEBUG=true
```

### Add Your Documents

Place your markdown (`.md`) or text (`.txt`) documents in the `documents/` directory:

```
documents/
├── employee-handbook.md
├── safety-procedures.md
└── faq.txt
```

### Run

```bash
# Start the development server
uv run uvicorn src.main:app --reload --port 8000
```

Visit [http://localhost:8000](http://localhost:8000) to start asking questions.

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

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENROUTER_API_KEY` | API key for LLM provider | Required |
| `OPENAI_API_KEY` | API key for embeddings/moderation | Required |
| `JWT_SECRET_KEY` | Secret for JWT token signing | Required |
| `LLM_MODEL` | Primary LLM model | `anthropic/claude-sonnet-4` |
| `LLM_FALLBACK_MODEL` | Fallback model | `anthropic/claude-haiku` |
| `RAG_CHUNK_SIZE` | Document chunk size (chars) | `1500` |
| `RAG_TOP_K` | Number of chunks to retrieve | `5` |
| `RATE_LIMIT_REQUESTS` | Requests per window | `10` |
| `CACHE_ENABLED` | Enable semantic caching | `true` |
| `AUTH_ENABLED` | Require authentication | `true` |

See `.env.example` for the complete list of configuration options.

### Document Preparation

For best results:

- Use **markdown format** with clear headings (`#`, `##`, `###`)
- Keep sections focused on single topics
- Use descriptive headings that match how users ask questions
- Include relevant keywords naturally in the text

## Deployment

Retriever can be deployed to any platform that supports Python applications.

### Railway / Render

1. Connect your repository
2. Set environment variables in the dashboard
3. Deploy

### Docker

```dockerfile
# Dockerfile example
FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install uv && uv sync
CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Production Checklist

- [ ] Set `DEBUG=false`
- [ ] Use a strong `JWT_SECRET_KEY`
- [ ] Configure rate limiting appropriately
- [ ] Set up monitoring (Sentry DSN in `SENTRY_DSN`)
- [ ] Use persistent storage for `data/` directory

## Architecture

Retriever uses a modular monolith architecture with clean separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                    DOCUMENT PIPELINE                         │
│  [Markdown/Text] → [Chunker] → [Embeddings] → [Vector DB]    │
└─────────────────────────────────────────────────────────────┘
                                                    ↓
┌─────────────────────────────────────────────────────────────┐
│                      QUERY FLOW                              │
│  [Question] → [Hybrid Search] → [Rerank] → [LLM] → [Answer]  │
└─────────────────────────────────────────────────────────────┘
```

**Tech Stack:**
- **Backend:** Python 3.12+, FastAPI, Pydantic
- **LLM:** Claude via OpenRouter
- **Vector DB:** Chroma (embedded)
- **Frontend:** Jinja2 + HTMX + Tailwind CSS
- **Database:** SQLite

## Development

```bash
# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=term-missing

# Linting and formatting
uv run ruff check src/ tests/ --fix
uv run ruff format src/ tests/

# Type checking
uv run mypy src/ --strict
```

## Documentation

- [Architecture Overview](docs/architecture.md)
- [Development Standards](docs/development-standards.md)
- [Implementation Roadmap](docs/increments.md)
- [Deployment Guide](docs/guides/deployment.md)
- [Adding Documents](docs/guides/adding-documents.md)

## License

MIT

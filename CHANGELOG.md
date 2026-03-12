# CHANGELOG

<!-- version list -->

## [Unreleased] — Stack Migration

### Added
- `backend/` — standalone uv Python project (`retriever` package, Python 3.13+)
- FastAPI app with `/health` endpoint, CORS middleware (explicit origins, no wildcards)
- pydantic-settings `Settings` with `SecretStr` for all secrets, wildcard-origin validator
- Cloudflare AI Gateway computed `ai_gateway_base_url` field
- structlog JSON logging + OpenTelemetry tracing bootstrap (console exporter in dev)
- `docker-compose.yml` — backend + pgvector/pg17 Postgres
- `docker-compose.test.yml` — ephemeral test Postgres (tmpfs, port 5433)
- `.env.example` updated to new stack schema

## v1.1.0 (2025-12-27)

### Bug Fixes

- Add missing documents module to git ([#16](https://github.com/ckrough/retriever/pull/16),
  [`b38b865`](https://github.com/ckrough/retriever/commit/b38b8655aef3c03ae7fcbb1742fb71dc8714d11e))

### Features

- Add document management via admin web interface
  ([#16](https://github.com/ckrough/retriever/pull/16),
  [`b38b865`](https://github.com/ckrough/retriever/commit/b38b8655aef3c03ae7fcbb1742fb71dc8714d11e))

### Testing

- Add comprehensive tests for documents module ([#16](https://github.com/ckrough/retriever/pull/16),
  [`b38b865`](https://github.com/ckrough/retriever/commit/b38b8655aef3c03ae7fcbb1742fb71dc8714d11e))


## v1.0.0 (2025-12-27)

- Initial Release

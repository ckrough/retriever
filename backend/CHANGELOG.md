# CHANGELOG

<!-- version list -->

## v1.3.0 (2026-03-16)

### Chores

- Add easyocr dependency for Docling PDF OCR ([#23](https://github.com/ckrough/retriever/pull/23),
  [`f16b724`](https://github.com/ckrough/retriever/commit/f16b724bd40a70588b23aeb5148a02bbbf97d3b7))

- Update GitHub Actions to Node.js 24-compatible versions
  ([#23](https://github.com/ckrough/retriever/pull/23),
  [`f16b724`](https://github.com/ckrough/retriever/commit/f16b724bd40a70588b23aeb5148a02bbbf97d3b7))

### Features

- Replace custom parser+chunker with Docling for multi-format document processing
  ([#23](https://github.com/ckrough/retriever/pull/23),
  [`f16b724`](https://github.com/ckrough/retriever/commit/f16b724bd40a70588b23aeb5148a02bbbf97d3b7))


## v1.2.0 (2026-03-16)

### Bug Fixes

- Add OTLP endpoint to pydantic settings to unblock Jaeger tracing
  ([#22](https://github.com/ckrough/retriever/pull/22),
  [`fc25d0f`](https://github.com/ckrough/retriever/commit/fc25d0fd4e819b277435949d1382ff9c5f4de5b7))

- Add PUBLIC_* env vars to CI frontend jobs ([#22](https://github.com/ckrough/retriever/pull/22),
  [`fc25d0f`](https://github.com/ckrough/retriever/commit/fc25d0fd4e819b277435949d1382ff9c5f4de5b7))

- Resolve review findings — OTLP dep, auth caching, JWT validation, CI hardening
  ([#22](https://github.com/ckrough/retriever/pull/22),
  [`fc25d0f`](https://github.com/ckrough/retriever/commit/fc25d0fd4e819b277435949d1382ff9c5f4de5b7))

### Documentation

- Add Google Cloud Run deployment guide ([#18](https://github.com/ckrough/retriever/pull/18),
  [`317079d`](https://github.com/ckrough/retriever/commit/317079d5446c1e9dc8239cc4510188fd08ce8455))

- Add pre-PR testing script for stack migration verification
  ([#22](https://github.com/ckrough/retriever/pull/22),
  [`fc25d0f`](https://github.com/ckrough/retriever/commit/fc25d0fd4e819b277435949d1382ff9c5f4de5b7))

- Update documentation for new stack architecture
  ([#22](https://github.com/ckrough/retriever/pull/22),
  [`fc25d0f`](https://github.com/ckrough/retriever/commit/fc25d0fd4e819b277435949d1382ff9c5f4de5b7))

### Features

- Add backend Python project skeleton (Phase 1)
  ([#22](https://github.com/ckrough/retriever/pull/22),
  [`fc25d0f`](https://github.com/ckrough/retriever/commit/fc25d0fd4e819b277435949d1382ff9c5f4de5b7))

- Add CI/CD, dev workflow, and docs cleanup (Phase 9)
  ([#22](https://github.com/ckrough/retriever/pull/22),
  [`fc25d0f`](https://github.com/ckrough/retriever/commit/fc25d0fd4e819b277435949d1382ff9c5f4de5b7))

- Add database layer with pgvector and Alembic migrations (Phase 3)
  ([#22](https://github.com/ckrough/retriever/pull/22),
  [`fc25d0f`](https://github.com/ckrough/retriever/commit/fc25d0fd4e819b277435949d1382ff9c5f4de5b7))

- Add JWKS-based auth module (Phase 4) ([#22](https://github.com/ckrough/retriever/pull/22),
  [`fc25d0f`](https://github.com/ckrough/retriever/commit/fc25d0fd4e819b277435949d1382ff9c5f4de5b7))

- Add LLM Gateway module (Phase 5) ([#22](https://github.com/ckrough/retriever/pull/22),
  [`fc25d0f`](https://github.com/ckrough/retriever/commit/fc25d0fd4e819b277435949d1382ff9c5f4de5b7))

- Add observability stack (Phase 6) ([#22](https://github.com/ckrough/retriever/pull/22),
  [`fc25d0f`](https://github.com/ckrough/retriever/commit/fc25d0fd4e819b277435949d1382ff9c5f4de5b7))

- Add RAG pipeline port (Phase 7) ([#22](https://github.com/ckrough/retriever/pull/22),
  [`fc25d0f`](https://github.com/ckrough/retriever/commit/fc25d0fd4e819b277435949d1382ff9c5f4de5b7))

- Add SvelteKit features — auth, chat, admin, docs (Phase 8)
  ([#22](https://github.com/ckrough/retriever/pull/22),
  [`fc25d0f`](https://github.com/ckrough/retriever/commit/fc25d0fd4e819b277435949d1382ff9c5f4de5b7))

- Add SvelteKit frontend skeleton (Phase 2) ([#22](https://github.com/ckrough/retriever/pull/22),
  [`fc25d0f`](https://github.com/ckrough/retriever/commit/fc25d0fd4e819b277435949d1382ff9c5f4de5b7))

- Complete stack migration — FastAPI + SvelteKit + pgvector + Supabase Auth
  ([#22](https://github.com/ckrough/retriever/pull/22),
  [`fc25d0f`](https://github.com/ckrough/retriever/commit/fc25d0fd4e819b277435949d1382ff9c5f4de5b7))

- Remove legacy monolith and consolidate to new stack (Phase 10)
  ([#22](https://github.com/ckrough/retriever/pull/22),
  [`fc25d0f`](https://github.com/ckrough/retriever/commit/fc25d0fd4e819b277435949d1382ff9c5f4de5b7))

### Testing

- Add automated integration tests for backend API verification
  ([#22](https://github.com/ckrough/retriever/pull/22),
  [`fc25d0f`](https://github.com/ckrough/retriever/commit/fc25d0fd4e819b277435949d1382ff9c5f4de5b7))


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

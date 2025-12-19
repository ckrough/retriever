# Implementation Roadmap

Agile vertical slices - each increment delivers a working, visible feature.

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

## Increment 1: Walking Skeleton

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
- [x] Project setup (pyproject.toml, dev container)
- [x] FastAPI app with single route
- [x] Jinja2 template with Tailwind (chat UI)
- [x] HTMX for form submission
- [x] Hardcoded response (no LLM yet)
- [x] Health endpoint `/health`
- [x] Input validation (1-2000 chars) *(added during code review)*
- [x] XSS prevention tests *(added during code review)*

**Validates:** Dev environment, FastAPI, HTMX, Tailwind, deployment pipeline

**Status:** ✅ Complete (PR #1)

---

## Increment 2: Real LLM Integration

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
- [x] OpenRouter provider (Protocol-based)
- [x] Environment config for API keys
- [x] Loading spinner in UI *(HTMX built-in from Increment 1)*
- [x] Error handling + display
- [x] Request timeouts (30s for LLM calls)
- [x] Circuit breaker for LLM calls (fail fast after 5 failures)
- [x] Rate limiting (10 requests/minute per session)
- [x] Input validation (max 2000 chars, basic sanitization) *(done in Increment 1)*

**Validates:** LLM integration, provider abstraction, error handling, resilience

**Status:** ✅ Complete

---

## Increment 3: Single Document RAG

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
- [ ] Text chunker (structure-aware)
- [ ] OpenAI embeddings
- [ ] Chroma vector store
- [ ] RAG pipeline (retrieve + generate)
- [ ] Admin page to trigger indexing
- [ ] Show retrieved chunks in response

**Validates:** Full RAG pipeline, chunking strategy, retrieval quality

---

## Increment 4: Multi-Document Support

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

## Increment 5: RAG Quality Hardening

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

## Increment 6: Content Safety

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

## Increment 7: User Authentication

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

## Increment 8: Conversation History

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

## Increment 9: Q&A Audit Logging

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

## Increment 10: Observability & Monitoring

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

## Increment 11: Feedback & Improvement

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

## Increment 12: Mobile Polish

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

## Increment 13: Production Deployment

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

## Future: Production Hardening

See [implementation-plan.md](implementation-plan.md#future-production-hardening-post-validation) for operational excellence items deferred until product validation.

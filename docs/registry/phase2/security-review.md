# Phase 2 — Security Review Findings

> Created: 2026-04-28 | Source: Security review of Phase 1+2 implementation
> Rule: development-process.md §9 — all Critical/High findings must clear before Phase 3 starts.
> Status key: ⏳ Pending · 🔄 In Progress · ✅ Fixed · ⚠️ Deferred

---

## Finding Registry

| ID | Severity | Status | Category | Summary | Depends On | Assigned To |
|----|----------|--------|----------|---------|------------|-------------|
| S01 | Critical | ⏳ Pending | Secrets | Real Azure OpenAI, Tavily, and frontend API keys committed in `backend/.env` and `frontend/.env` | — | backend-developer |
| S02 | Critical | ⏳ Pending | Path Traversal | User-supplied `data_dir` in `/ingest` body used as raw `Path` with no boundary enforcement | — | backend-developer |
| S03 | High | ⏳ Pending | Secrets | `langsmith_api_key` typed `str`, not `SecretStr` — violates SecretStr boundary rule | — | backend-developer |
| S04 | High | ⏳ Pending | Prompt Injection | User query concatenated verbatim into grader and critic prompts without structural separation | — | backend-developer |
| S05 | High | ⏳ Pending | Deserialisation | BM25 index loaded with `pickle.load` — arbitrary code execution if file is tampered | — | backend-developer |
| S06 | High | ⏳ Pending | DoS | No rate limiting on `/query`, `/query/agentic`, or `/ingest`; LLM cost exhaustion | — | backend-developer |
| S07 | High | ⏳ Pending | CORS | `CORS_ORIGINS=["*"]` in `backend/.env`; wildcard default in `.env.example` | — | backend-developer |
| S08 | High | ⏳ Pending | Auth | Qdrant starts with no API key and ports published to host | — | backend-developer |
| S09 | Major | ⏳ Pending | Race Condition | `BM25Store.build()` and query reads share state without an asyncio lock | — | backend-developer |
| S10 | Major | ⏳ Pending | Input Validation | `QueryRequest.query` has no `max_length`; unbounded payload enables DoS | — | backend-developer |
| S11 | Major | ⏳ Pending | Data Exposure | Full `page_content` texts emitted as `retrieved_contexts` in citations SSE event | — | backend-developer |
| S12 | Major | ⏳ Pending | Config | `builder.py:52` hardcodes `"gpt-4o-mini"` instead of settings reference | — | backend-developer |
| S13 | Major | ⏳ Pending | Transport | `qdrant_url` defaults to plaintext `http://`; no TLS enforcement in production | — | backend-developer |
| S14 | Major | ⏳ Pending | Path Traversal | SQLite checkpointer path resolved with `mkdir -p` and no boundary validation | — | backend-developer |
| S15 | Minor | ⏳ Pending | Ops | `docker-compose.yml` binds `/Users/kalai/qdrant_storage` — developer-specific absolute host path | — | backend-developer |
| S16 | Minor | ⏳ Pending | Input Validation | Client-supplied `X-Session-ID` used as SQLite thread_id without UUID format validation | — | backend-developer |
| S17 | Minor | ⏳ Pending | Info Disclosure | Raw exception strings (Qdrant URLs, file paths) forwarded to HTTP clients via `exc.message` | — | backend-developer |
| S18 | Minor | ⏳ Pending | DoS | No maximum request body size at Uvicorn or FastAPI layer | — | backend-developer |
| S19 | Advisory | ⏳ Pending | Privacy | LangSmith tracing sends query/document content to third-party US service; no DPA documented | — | backend-developer |
| S20 | Advisory | ⏳ Pending | Dependencies | No `pip-audit` or Dependabot; CVEs in pinned versions go undetected | — | backend-developer |

---

## Detailed Findings

### S01 — Real Secrets Committed to Repository (Critical)

**File:** `backend/.env:2`, `backend/.env:26`, `frontend/.env:4`
**Issue:** `backend/.env` contains a live Azure OpenAI API key and a live Tavily API key. `frontend/.env` contains a real API key value. Any contributor or attacker with access to the git object store possesses credentials granting access to billed Azure OpenAI and Tavily resources.
**Fix:** Immediately revoke and rotate all three credentials. Purge the secrets from git history using `git filter-repo` or BFG Repo Cleaner. Replace with Azure Key Vault references in production; use only placeholder values in `.env.example`. Add a `detect-secrets` pre-commit hook.
**Rule/CWE:** python-rules.md §Secrets; CWE-312; OWASP A02.

---

### S02 — Path Traversal via User-Controlled `data_dir` in Ingest Endpoint (Critical)

**File:** `backend/src/api/routes/ingest.py:34`, `backend/src/ingestion/pipeline.py:73`
**Issue:** `IngestRequest` accepts `data_dir: str | None` from the HTTP body, passed directly to `Path(body.data_dir)` and given to `LocalFileLoader` with no assertion that the resolved path is a descendant of `settings.data_dir`. A caller can supply `"../../../etc"` or any absolute path to ingest arbitrary host files.
**Fix:** After constructing the resolved path, assert `resolved_path.resolve().is_relative_to(Path(settings.data_dir).resolve())` and reject with HTTP 422 on failure. Also constrain `data_dir` in the schema to reject `..` path components.
**Rule/CWE:** CWE-22 (Path Traversal); OWASP A01.

---

### S03 — `langsmith_api_key` Typed `str` Instead of `SecretStr` (High)

**File:** `backend/src/config.py:52`
**Issue:** `langsmith_api_key: str = ""` is the only credential field in `Settings` not typed as `SecretStr`. The value appears in plaintext in `settings.model_dump()` output and will be serialised by structlog if the settings object is logged.
**Fix:** Change to `langsmith_api_key: SecretStr = SecretStr("")` and update all call sites to use `.get_secret_value()`.
**Rule/CWE:** python-rules.md §Secrets — SecretStr boundary rule; CWE-312; OWASP A02.

---

### S04 — Prompt Injection via Unguarded User Query in Grader and Critic Nodes (High)

**File:** `backend/src/graph/nodes/grader.py:82–86`, `backend/src/graph/nodes/critic.py:58–62`
**Issue:** The raw user query is interpolated directly into the `user` role message in both the grader (`f"Query: {query}\n\n..."`) and critic (`f"Question: {query}\n\n..."`). A crafted query can manipulate scoring LLMs to assign arbitrary scores or leak their system prompts via the `reasoning` field.
**Fix:** Wrap user-controlled content in XML-style delimiters (e.g. `<user_query>...</user_query>`) and instruct the LLM in the system prompt to treat content inside those tags as untrusted data. Validate that structured output fields (`score`, `hallucination_risk`) are within `[0.0, 1.0]` before trusting them.
**Rule/CWE:** OWASP LLM01 (Prompt Injection); CWE-77.

---

### S05 — Unsafe `pickle.load` on BM25 Index File (High)

**File:** `backend/src/ingestion/bm25_store.py:74–75`
**Issue:** `BM25Store.load()` calls `pickle.load(fh)` on the file at `settings.bm25_index_path`. The `# noqa: S301` suppressor acknowledges but does not mitigate the risk. If the container volume is writable by an attacker (enabled by S02 or a compromised pipeline), a malicious pickle payload yields arbitrary code execution inside the application process.
**Fix:** Replace pickle with JSON serialisation (store tokenised corpus as a JSON array and rebuild `BM25Okapi` on load). If pickle must be retained, compute and verify an HMAC-SHA256 checksum against a server-side key before loading.
**Rule/CWE:** CWE-502 (Deserialization of Untrusted Data); OWASP A08.

---

### S06 — No Rate Limiting on Query or Ingest Endpoints (High)

**File:** `backend/src/api/main.py` (no rate-limit middleware registered)
**Issue:** A single authenticated client can issue unlimited requests to `/query/agentic`, each triggering five LLM calls (router, grader, critic, generator, plus embeddings), directly burning Azure OpenAI quota without bound.
**Fix:** Add per-client rate limiting using `slowapi` as FastAPI middleware (e.g. 30 req/min per IP for query endpoints, 5 req/min for ingest). For production, front with Azure API Management for quota management.
**Rule/CWE:** OWASP A04 (Insecure Design); CWE-770.

---

### S07 — CORS Wildcard `"*"` Active in Both `.env` and `.env.example` (High)

**File:** `backend/.env:10`, `backend/.env.example:10`, `backend/src/api/main.py:88–93`
**Issue:** `CORS_ORIGINS=["*"]` is set in the committed `.env`. `CORSMiddleware` also has `allow_methods=["*"]` and `allow_headers=["*"]`. Any origin can make cross-origin requests.
**Fix:** Set `CORS_ORIGINS` to an explicit list of allowed frontend origins. Update `.env.example` to a placeholder. Enumerate only required methods (`POST`, `GET`) and headers (`Content-Type`, `X-API-Key`, `X-Session-ID`).
**Rule/CWE:** OWASP A05; CWE-942.

---

### S08 — Qdrant Exposed Without Authentication or TLS (High)

**File:** `infra/docker-compose.yml:3–14`
**Issue:** Qdrant starts with no API key and no TLS. Ports `6333` and `6334` are published to `0.0.0.0`. Any process reaching the host can read, write, or delete all vector data without credentials.
**Fix:** Set `QDRANT__SERVICE__API_KEY` in `docker-compose.yml` (from an env var). Configure `AsyncQdrantClient` with the matching `api_key` parameter. For production on Azure, deploy Qdrant behind a private endpoint with TLS.
**Rule/CWE:** OWASP A01; CWE-306.

---

### S09 — BM25Store Read/Write Race Condition (Major)

**File:** `backend/src/ingestion/bm25_store.py`, `backend/src/ingestion/pipeline.py:160–161`
**Issue:** `BM25Store.build()` and `save()` are called by the background ingestion pipeline while `SparseRetriever.search()` reads `self._index` and `self._chunks` from concurrent query coroutines. No asyncio lock protects these shared in-memory attributes.
**Fix:** Introduce an `asyncio.Lock` on `BM25Store`. Build into local variables and atomically replace `self._index`/`self._chunks` only after the build completes (copy-on-write pattern).
**Rule/CWE:** CWE-362 (Concurrent Execution Using Shared Resource with Improper Synchronization).

---

### S10 — No `max_length` on `QueryRequest.query` Field (Major)

**File:** `backend/src/api/schemas/__init__.py:47`
**Issue:** `query: str = Field(..., min_length=1)` has no upper bound. `AgentQueryRequest` correctly applies `max_length=2000`; this was not mirrored in `QueryRequest`. An unbounded query string passed to Azure OpenAI embedding can exhaust tokens and memory.
**Fix:** Add `max_length=2000` to the `query` field in `QueryRequest`.
**Rule/CWE:** CWE-770; OWASP A04.

---

### S11 — Full Document Chunk Texts Emitted in SSE `citations` Event (Major)

**File:** `backend/src/api/routes/query_agentic.py:139`
**Issue:** The `citations` SSE event includes `'retrieved_contexts': _context_texts` — raw `page_content` strings from all graded documents. Every querying client receives verbatim source document text, bypassing any document-level access control required in multi-tenant scenarios.
**Fix:** Remove `retrieved_contexts` from the SSE wire format. If needed for evaluation, gate its emission behind an internal-only flag verified by middleware.
**Rule/CWE:** OWASP LLM06 (Sensitive Information Disclosure); CWE-200.

---

### S12 — Hardcoded LLM Deployment Name in Graph Builder (Major)

**File:** `backend/src/graph/builder.py:52`
**Issue:** `AzureChatOpenAI(azure_deployment="gpt-4o-mini", ...)` at line 52 hardcodes a string literal, while line 58 correctly uses `settings.azure_chat_deployment`. Router, grader, and critic nodes always use `"gpt-4o-mini"` regardless of environment configuration, creating a hidden configuration fork.
**Fix:** Replace `azure_deployment="gpt-4o-mini"` with `azure_deployment=settings.azure_chat_deployment` or introduce a dedicated `settings.azure_mini_deployment` field if a distinct deployment is intentional.
**Rule/CWE:** python-rules.md §No Hardcoded Values; CWE-1188.

---

### S13 — Qdrant URL Defaults to Plaintext HTTP (Major)

**File:** `backend/src/config.py:31`
**Issue:** `qdrant_url: str = "http://localhost:6333"` and no validator rejects plaintext HTTP URLs in production. All vector data and query embeddings are transmitted in cleartext when misconfigured.
**Fix:** Add a `@field_validator('qdrant_url')` that rejects `http://` URLs when `APP_ENV=production`. Document in `.env.example` that production deployments must use `https://` or a private-endpoint URL.
**Rule/CWE:** OWASP A02; CWE-319.

---

### S14 — SQLite Checkpointer Path Created Without Boundary Validation (Major)

**File:** `backend/src/graph/builder.py:110–112`
**Issue:** `checkpointer_path = Path(settings.sqlite_checkpointer_path)` is resolved and `mkdir -p` is called unconditionally with no validation that the path is within the application data directory.
**Fix:** Validate that `sqlite_checkpointer_path` resolves to a path under `settings.data_dir` using `is_relative_to`, consistent with the fix for S02.
**Rule/CWE:** CWE-22; OWASP A05.

---

### S15 — Developer-Specific Absolute Host Path in docker-compose.yml (Minor)

**File:** `infra/docker-compose.yml:8`
**Issue:** `volumes: - /Users/kalai/qdrant_storage:/qdrant/storage` binds an absolute macOS home-directory path, failing or using an unintended location on any other machine. The developer path is committed to source control.
**Fix:** Replace the absolute host path with the named Docker volume `qdrant_storage` already declared in the top-level `volumes:` block.
**Rule/CWE:** CWE-200; operational hygiene.

---

### S16 — `X-Session-ID` Not Validated Before Use as SQLite Thread ID (Minor)

**File:** `backend/src/api/routes/query_agentic.py:87`
**Issue:** `session_id = request.headers.get("X-Session-ID") or str(uuid.uuid4())` trusts the client-supplied value directly as the LangGraph `thread_id` without length, character, or format validation. A client can supply another user's session ID to read their conversation history.
**Fix:** Validate `X-Session-ID` as a UUID4 string (`uuid.UUID(session_id, version=4)`) and reject non-conforming values with HTTP 400.
**Rule/CWE:** CWE-20 (Improper Input Validation); OWASP A01.

---

### S17 — Internal Exception Strings Forwarded to HTTP Clients (Minor)

**File:** `backend/src/api/main.py:127`, `main.py:139`, `main.py:151`
**Issue:** Exception handlers return `ErrorResponse(detail=exc.message)`, where `exc.message` contains raw upstream exception strings including Qdrant endpoint URLs, collection names, and internal file paths.
**Fix:** Return a generic message (e.g. `"Vector store search failed"`) in HTTP exception handlers. Retain full detail in the structured log at `error` level only.
**Rule/CWE:** OWASP A05; CWE-209.

---

### S18 — No Maximum Request Body Size Enforced (Minor)

**File:** `backend/Dockerfile:44`, `backend/src/api/main.py`
**Issue:** Uvicorn starts without a body-size limit. A multi-megabyte JSON body posted to any endpoint consumes memory and blocks the async event loop during parsing.
**Fix:** Add a `ContentSizeLimitMiddleware` rejecting requests exceeding a configured limit (e.g. 1 MB for query, 10 MB for ingest). Also set `--limit-concurrency` on the Uvicorn command.
**Rule/CWE:** CWE-400; OWASP A04.

---

### S19 — LangSmith Tracing Sends Query/Document Data to Third-Party Service (Advisory)

**File:** `backend/src/config.py:52–53`
**Issue:** When `LANGCHAIN_TRACING_V2=true`, LangChain sends all LLM inputs and outputs — including user queries and retrieved document text — to LangSmith's cloud service. No Data Processing Agreement with LangSmith is documented. Combined with S03 (`langsmith_api_key` typed as `str`), the key is also visible in logs.
**Fix:** Keep `LANGCHAIN_TRACING_V2=false` in production. If tracing is needed, evaluate LangSmith's data residency options, obtain a DPA, and restrict to non-production environments. Also resolve S03.
**Rule/CWE:** GDPR Art. 28; OWASP LLM06.

---

### S20 — No Automated Dependency Vulnerability Scanning (Advisory)

**File:** `backend/pyproject.toml`
**Issue:** All dependencies use `^` or `~` constraints without automated CVE scanning. `pip-audit`, `safety`, Dependabot, and Renovate are absent. A disclosed CVE after the last `poetry.lock` update will be silently present. Note: CVE-2025-29927 (Next.js middleware auth bypass, CVSS 9.1) affects all Next.js versions before 14.2.25 / 15.2.3 — the frontend version must be verified immediately.
**Fix:** Add `pip-audit` to CI as a blocking gate. Enable GitHub Dependabot or Renovate Bot. Commit and regularly regenerate `poetry.lock`.
**Rule/CWE:** OWASP A06 (Vulnerable and Outdated Components).

---

## Dependency Audit

| Package | Constraint | CVE / Advisory | CVSS | Fixed In |
|---------|-----------|----------------|------|----------|
| `next` (frontend) | Not reviewed | CVE-2025-29927 middleware auth bypass | 9.1 Critical | 14.2.25 / 15.2.3 |
| `langchain` | `~0.3.28` | No known CVE at 0.3.28 as of 2026-04-28 | — | — |
| `langgraph` | `~0.2.76` | No known CVE at 0.2.76 as of 2026-04-28 | — | — |
| `fastapi` | `^0.115` | No known CVE at 0.115.x as of 2026-04-28 | — | — |
| `qdrant-client` | `^1.12` | No known CVE at 1.12.x as of 2026-04-28 | — | — |
| `pypdf` | `^5.1` | No known CVE at 5.1.x as of 2026-04-28 | — | — |

---

## Compliance Notes

**Secrets in git history (S01):** The committed `backend/.env` contains live credentials. Any repository access — forks, CI logs, exports — constitutes a breach. Rotation and history purge are the highest-priority actions.

**GDPR:** User queries and document content are sent to Azure OpenAI. If any content contains personal data, a DPA with Microsoft (GDPR Art. 28) is required, and the Azure OpenAI processing region must match required data residency. LangSmith tracing (S19) routes data to a US cloud service and requires a separate DPA.

**PII in logs:** Router, critic, and retriever failure paths log `query=query` (full query string), which may capture PII. Change to `query_len=len(query)` in all failure-path log events.

**Data retention:** The SQLite checkpointer retains full conversation history indefinitely. If the system processes personal data, this violates GDPR Art. 5(1)(e) (storage limitation). A TTL and purge mechanism are required (see architect-fixes.md F17).

---

## Remediation Order

**Batch 1 — Immediate (before any further code is merged):**
S01 (rotate credentials, purge git history), S07 (remove CORS wildcard)

**Batch 2 — Before Phase 3 starts (Critical/High blockers):**
S02 (path boundary validation), S05 (replace pickle), S08 (Qdrant auth), S06 (rate limiting), S03 (langsmith SecretStr), S04 (prompt injection delimiters)

**Batch 3 — Major hardening (complete within Phase 3):**
S10 (max_length on QueryRequest), S11 (remove retrieved_contexts from SSE), S12 (hardcoded deployment name), S09 (BM25 asyncio lock), S13 (Qdrant TLS validator), S14 (checkpointer path boundary)

**Batch 4 — Minor / Advisory:**
S16, S17, S18, S15, S19, S20

---

## Verification Checklist

- [ ] S01 — credentials rotated, git history scrubbed, `detect-secrets` hook active
- [ ] S02 — `is_relative_to` guard present; path traversal test cases pass
- [ ] S03 — `langsmith_api_key` type is `SecretStr`; `mypy --strict` passes
- [ ] S04 — XML delimiters present in grader and critic prompts
- [ ] S05 — pickle replaced with JSON or HMAC-verified format
- [ ] S06 — rate limit middleware present; load test confirms rejection at threshold
- [ ] S07 — `CORS_ORIGINS` is an explicit list in all environment configs
- [ ] S08 — Qdrant API key set; ports not published to public interface in production
- [ ] S09 — asyncio lock added; concurrent ingest + query test passes
- [ ] S10 — `max_length=2000` on `QueryRequest.query`
- [ ] S11 — `retrieved_contexts` removed from SSE citations event
- [ ] S12 — hardcoded `"gpt-4o-mini"` replaced with settings reference
- [ ] S13 — plaintext Qdrant URL rejected in production environment mode
- [ ] S14 — SQLite path boundary check present
- [ ] S15 — named Docker volume replaces absolute host path
- [ ] S16 — UUID4 validation on `X-Session-ID`; non-conforming values return HTTP 400
- [ ] S17 — error responses return generic messages; detail in structured logs only
- [ ] S18 — body size middleware present; oversized requests rejected with 413
- [ ] S19 — LangSmith tracing disabled in production; DPA assessment documented
- [ ] S20 — `pip-audit` in CI pipeline; Dependabot configured

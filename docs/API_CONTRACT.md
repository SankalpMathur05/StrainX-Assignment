# API contract (`/api/py/*`)

Models: `backend/app/models.py` (Python) ↔ `lib/types.ts` (TS). All routes return JSON.
Dev: FastAPI on `http://127.0.0.1:8000`, Next.js rewrites `/api/py/:path*` to it. Prod (Vercel): `api/index.py`.

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/api/py/health` | – | `Health` |
| GET | `/api/py/requisitions` | – | `Requisition[]` (newest first; seed PR-USP-1147 always present on a fresh store) |
| POST | `/api/py/requisitions` | `Requisition` (no id) | `Requisition` (with id) |
| GET | `/api/py/requisitions/{id}` | – | `Requisition` (404 if missing) |
| PUT | `/api/py/requisitions/{id}` | `Requisition` | `Requisition` |
| DELETE | `/api/py/requisitions/{id}` | – | `{"deleted": true}` (cascades quotes, runs, chat) |
| GET | `/api/py/requisitions/{id}/quotes` | – | `Quote[]` (ordered by label) |
| POST | `/api/py/requisitions/{id}/quotes` | `Quote` | `Quote` (requisition_id set from path; label auto-assigned A, B, … if blank) |
| PUT | `/api/py/quotes/{id}` | `Quote` | `Quote` |
| DELETE | `/api/py/quotes/{id}` | – | `{"deleted": true}` |
| POST | `/api/py/compare` | `CompareRequest` | `CompareResult` (stateless) |
| POST | `/api/py/requisitions/{id}/compare` | `{weights?, reference_date?}` | `CompareResult` (loads requisition + quotes from storage) |
| GET | `/api/py/comparisons?requisition_id=` | – | `ComparisonRun[]` (newest first) |
| POST | `/api/py/comparisons` | `ComparisonRunCreate` | `ComparisonRun` (server computes and snapshots the result) |
| GET | `/api/py/comparisons/{id}` | – | `ComparisonRun` |
| GET | `/api/py/requisitions/{id}/chat` | – | `ChatMessage[]` (oldest first) |
| POST | `/api/py/extract/requisition` | `ExtractRequest` | `ExtractResponse` (`fields` = partial `Requisition`) |
| POST | `/api/py/extract/quote` | `ExtractRequest` | `ExtractResponse` (`fields` = partial `Quote`) |
| POST | `/api/py/insights` | `InsightsRequest` | `InsightsResponse` |
| POST | `/api/py/chat` | `ChatRequest` | `ChatResponse` (user + assistant messages persisted when `requisition_id` set) |

## No Groq key
AI routes return **HTTP 200** with `available: false` and
`message: "AI features are off: add GROQ_API_KEY to .env.local (see .env.example) and restart. All calculations, flags and recommendations still work without it."`
`/insights` in that case still returns `headline` = the deterministic recommendation rationale and
`supplier_questions` = the engine's per-quote questions, so the UI always has content.

## Errors
Validation errors: FastAPI default 422. Not found: 404 `{"detail": "..."}`.
AI provider failure (both primary and fallback model): 200 with `available: false` and a short `message`.

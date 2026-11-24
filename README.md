# StrainX Quote Compare

Turns messy supplier quotes (email, WhatsApp, PDF, phone notes) into a like-for-like comparison,
automatic risk flags and a recommendation a director can read in about a minute.
Pre-loaded with **PR-USP-1147 – Yeast Extract Powder, Quotes A–D**; works for any purchase.

**Prerequisites:** Node.js 20+ and [uv](https://docs.astral.sh/uv/getting-started/installation/) (uv fetches a suitable Python automatically).

## Run it (3 steps)

1. Install dependencies:
   ```bash
   npm install && uv sync
   ```
2. *(Optional, only for the AI features and Supabase)* copy the env template and add your keys:
   ```bash
   cp .env.example .env.local      # Windows: copy .env.example .env.local
   ```
3. Start the web app and the API together:
   ```bash
   npm run dev
   ```
   Open http://localhost:3000. API docs are at http://localhost:8765/api/py/docs.

Without any keys, the comparison engine, risk flags, scoring, priorities, copy/print and history all
work. Data is stored in `.data/local_db.json`, seeded with PR-USP-1147 on first run. Without
`GROQ_API_KEY`, the AI panels show a short setup message.

## Tests

```bash
uv run pytest                      # engine math, flags, scoring, API and AI routes (Groq mocked, offline)
npx tsc --noEmit && npm run build  # frontend type-check + production build
npm run verify                     # all of the above
```

## How it works

| Layer | Where | What it does |
|---|---|---|
| Engine | `backend/app/{units,costing,dates,flags,scoring,summary,engine}.py` | Deterministic Python: unit/pack/MOQ conversion, GST/import duty/IGST, freight, landed cost, delivery dates, risk flags, weighted scoring, rationale and share text. **No LLM arithmetic.** |
| API | `backend/app/main.py` → `/api/py/*` | FastAPI routes ([docs/API_CONTRACT.md](docs/API_CONTRACT.md)) |
| AI | `backend/app/ai/` | Groq: paste-to-fill extraction (requisitions and quotes), executive insights, chat. Every AI answer is checked for numbers that don't appear in the engine output. |
| Storage | `backend/app/repo/` | Supabase when `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` are set, otherwise a local JSON file |
| Web | `app/`, `components/`, `lib/` | Next.js dashboard (`/`), new requisition (`/requisitions/new`), quotes & history (`/history`) |

### Optional: Supabase
1. In your Supabase project's SQL editor, run `supabase/schema.sql` and then `supabase/seed.sql`.
2. Put `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` in `.env.local`. These keys are read only by the Python backend, never by the browser.

### Optional: deploy to Vercel
Import the repo in Vercel (framework: Next.js). `vercel.json` routes `/api/py/*` to the Python function `api/index.py`, which reads `requirements.txt`. If you change Python dependencies, regenerate that file with `uv export --no-dev --no-hashes -o requirements.txt`. Add the same env vars in the Vercel project settings.

Without Supabase, the deployed app falls back to `/tmp` storage, which is wiped between invocations, so use Supabase for persistence on Vercel.

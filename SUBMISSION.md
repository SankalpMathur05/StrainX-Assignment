# SUBMISSION

## A. Summary
<!-- Three lines: what you built, what you recommend for the yeast extract purchase, and what you are least sure about. -->

## B. Time log
<!-- Table: phase (understanding, planning, building, testing, writing), start, end, minutes. Give the total. -->

| Phase | Start | End | Minutes |
|---|---|---|---|
| | | | |
| **Total** | | | |

## C. How I understood the problem
<!-- What does the director really need? What did you build first, what did you decide not to build, and why? -->

## D. Decision log
<!-- 5 to 10 key decisions: the decision, options considered, what you chose, why, and what AI suggested if you asked it. -->

## E. Assumptions
<!-- Numbered list of every assumption about the data, the rules or the user. -->

## F. Analysis of the yeast extract purchase
<!-- Table with your numbers for each quote, the problems found in each, and your final ranking. -->

## G. How I used AI
<!-- Tools and what for; 3-5 most important prompts word for word; where AI was wrong and how you noticed; what you wrote or changed yourself; how you checked the calculations. -->

## H. My thinking vs the AI
<!-- What you found in Step 1 that AI missed or got wrong; what AI found that you missed; what changed between Step 1 and the final recommendation, and why. -->

## I. Testing

### How to run the tests
```bash
uv run pytest                      # all Python tests: engine, API, AI (Groq mocked, no network)
npx tsc --noEmit && npm run build  # frontend type-check + production build
npm run verify                     # runs all three in sequence
```

### What the tests cover
There are 171 automated tests, all passing, and they run offline. The test fixture removes every key from the environment and never reads `.env.local`. Groq is always replaced by a fake, and storage is a temporary JSON file.

| File | Tests | What it checks |
|---|---|---|
| `test_costing.py` | 24 | PR-USP-1147 Quotes A–D to the paisa: A Rs 2,27,150; B Rs 1,82,500 (incl. GST reading) and Rs 2,14,900 (GST extra); C Rs 4,47,456.16 for the 50 kg MOQ and Rs 2,30,978.08 if waived; D Rs 1,60,125 at 5% and Rs 1,79,950 at 18%, freight unknown. Also checks pack rounding, USD at Rs 84, customs 12%, IGST 18% on CIF + duty, clearance and inland transport, the free-freight threshold, inclusive-GST back-calculation and unit mismatch. |
| `test_units.py` | 15 | g/kg and mL/L conversion, count units, rounding up to whole packs or drums |
| `test_dates.py` | 13 | Mon–Sat working days, transit days, lead-time ranges (upper bound) against the need-by date |
| `test_flags.py` | 40 | Every flag trigger: expired quote, missing validity, late or tight delivery, MOQ above need, missing or conditional CoA, heavy advance, contradictory or unconfirmed tax, missing brand, over budget, verbal-only quote, unknown freight. Also the exact flag set for A–D. |
| `test_scoring.py` | 27 | Criterion scores, −30 per CRITICAL / −5 per WARNING penalty, seed scores (A 78.52, D 3.75, B −37.63, C −41.94), ranking A > D > B > C, a re-rank when the weights change, all-zero weights, rationale wording |
| `test_summary.py` | 14 | Indian number formatting (Rs 2,27,150; Rs 1,00,00,000), dates, the WhatsApp/email summary text |
| `test_api.py` | 17 | Health, requisition and quote CRUD (404s, auto labels A/B/…, cascade delete), compare, saved runs, chat history, real-engine end-to-end on the seed, Supabase only used when both env vars are set, `seed.sql` matches `seed.py` |
| `test_ai.py` | 21 | Mocked Groq: extraction drops unknown or invalid fields and reports missing ones, fallback model on failure, no-key message plus rule-based insights, chat saved to history, the number-grounding check (flags made-up numbers; ignores dates and rounding) |

### Manual checks (24 Nov 2026, with live Supabase and Groq)
- `npm run dev`, then the dashboard on the seed: A recommended at 78.5 with Rs 2,27,150 (+Rs 27,150 vs budget, of which Rs 34,650 is GST shown as potential ITC). Ranking A, D, B, C.
- Price-only weights: A 69.22, D 40.00. A still wins, because D's flag penalties outweigh its lower price.
- A saved run and chat messages were written to and read back from Supabase.
- AI insights (`openai/gpt-oss-120b`): no ungrounded numbers. Chat answered on the fallback model after the primary failed.
- Paste-to-fill on Quote D's phone note pulled price, GST, freight, lead time, payment, CoA and brand correctly. It set the supplier name to the contact ("Mr. Verma"), which is why every AI-filled field is reviewed before saving.
- Headless-browser screenshots: desktop light and dark themes, a 390 px phone width, and print-to-PDF (summary, comparison and risks fit on one page).

## J. Limitations and next steps
<!-- What does not work yet, what you would do with one more day, how this could fit into a company ERP. -->

## K. Declaration
<!-- One line: the work is your own, no other person helped, Step 1 was done without AI, AI use is fully disclosed. -->

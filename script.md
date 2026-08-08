# Application Script — Architecture, Components, and Flows

This document explains the starter repo: its architecture, main components, and the runtime flow for each task (Triage, Summariser, and the Evaluation Harness). It also includes run/CI instructions and pointers to the most relevant files for a deeper read.

## Purpose

The repository implements a production-style AI tooling suite for Technical Support and Technical Account Management (TAM) workflows. It contains:
- Task 1: Ticket triage agent — classifies incoming tickets and produces a draft response.
- Task 2: Account health summariser — generates deterministic account briefs for QBRs.
- Task 3: Evaluation harness — tests Tasks 1 & 2 and produces reports.

## High-level architecture

- `main.py` — CLI entrypoint. Commands: `serve`, `index`, `eval`, `ui`.
- `src/api.py` — FastAPI service exposing the triage and account-brief endpoints plus streaming variants.
- `src/triage/` — Triage schemas, prompts, and agent logic.
- `src/summariser/` — Account brief generator, prompts, and schemas.
- `src/rag/` — RAG indexer and retriever logic (builds the knowledge base index used for retrieval).
- `src/eval/` — Evaluation harness (`harness.py`), scoring (`scoring.py`), and test cases.
- `src/config.py` — Central configuration (environment variables such as `GROQ_API_KEY`, model name, data paths).
- `data/` — Mock datasets: `tickets.json`, `accounts.json` used by the agents and tests.
- `knowledge-base/` — Markdown docs used by RAG for KB-matching.
- `chroma_db/` — Persisted chroma index (managed by `src/rag/indexer.py`).
- `requirements.txt` — Python dependencies.

Relevant files to inspect:
- [main.py](main.py)
- [src/api.py](src/api.py)
- [src/eval/harness.py](src/eval/harness.py)
- [src/eval/scoring.py](src/eval/scoring.py)
- [src/triage/agent.py](src/triage/agent.py)
- [src/summariser/agent.py](src/summariser/agent.py)
- [src/rag/indexer.py](src/rag/indexer.py)
- [requirements.txt](requirements.txt)

## Runtime entrypoints

- Start the FastAPI server (serves REST endpoints):

```bash
python main.py serve --host 0.0.0.0 --port 8000
```

- Build or update the RAG index (used by triage & summariser):

```bash
python main.py index --force
```

- Run the evaluation harness (generates `eval_report.json` and `eval_report.md`):

```bash
export GROQ_API_KEY="<your_key>"
python main.py eval
```

- Start the Streamlit UI (if included):

```bash
python main.py ui
```

## Task flows

### Task 1 — Ticket Triage (overview)

1. Input: Either API call to `POST /triage` (see `src/api.py`) or internal function calls.
2. The triage agent (`src/triage/agent.py`) accepts `subject` and `body` (or a dataset `ticket_id`) and performs:
   - Retrieval: uses the RAG retriever to find relevant KB docs.
   - LLM prompt: assembles a prompt (from `src/triage/prompts.py`) containing ticket text + retrieved context.
   - Model call: calls the configured LLM client (via the `groq` client) to produce a structured `TriageResult`.
   - Post-processing: extract `issue_category`, `urgency_tier`, `recommended_team`, `draft_response`, and reasoning.
3. Output: a `TriageResult` model (Pydantic / dataclass schema) returned by the API or callable function.

Notes:
- The API exposes streaming via `/triage/stream` which yields SSE events from `triage_ticket_stream`.
- The agent uses deterministic settings where possible (see `src/config.py` for `TEMPERATURE` and `SEED`).

Files of interest: [src/triage/agent.py](src/triage/agent.py), [src/triage/prompts.py](src/triage/prompts.py), [src/triage/schemas.py](src/triage/schemas.py)

### Task 2 — Account Health Summariser (overview)

1. Input: `account_id` (API: `POST /account-brief`). The summariser pulls the account record from `data/accounts.json` and the last 90 days of tickets via `get_account_tickets`.
2. The summariser (`src/summariser/agent.py`) performs:
   - Data collection: compile structured account fields and recent tickets.
   - RAG retrieval: fetch KB context if relevant.
   - Prompting & generation: produce a 3-part brief: executive summary, open risks (with quoted evidence), and TAM talking points.
   - Determinism: controlled via `TEMPERATURE` and `SEED`, and by post-processing to remove stochastic elements.
3. Output: `AccountBrief` object with `executive_summary`, `open_risks`, and `talking_points`.

Streaming: `POST /account-brief/stream` uses `generate_account_brief_stream` to provide incremental updates.

Files of interest: [src/summariser/agent.py](src/summariser/agent.py), [src/summariser/prompts.py](src/summariser/prompts.py), [src/summariser/schemas.py](src/summariser/schemas.py)

### Task 3 — Evaluation Harness (overview)

1. Entry point: `main.py eval` runs `src.eval.harness.run_evals()`.
2. `EvalHarness.run_all()` iterates `TRIAGE_TEST_CASES` and `SUMMARISER_TEST_CASES` defined in `src/eval/test_cases.py`.
3. For each test:
   - Execute agent (triage or summariser).
   - Run rule-based checks (`src/eval/scoring.py`) to verify schema, enums, non-empty fields, and other deterministic assertions.
   - Run LLM-as-judge where configured via `llm_judge_triage` / `llm_judge_summariser` (this makes model calls via the `groq` client and thus requires `GROQ_API_KEY`).
   - Combine checks into a `quality_score` and determine pass/fail.
4. Reporting: `harness.generate_reports()` writes `eval_report.json` and `eval_report.md` to the project root.

Files of interest: [src/eval/harness.py](src/eval/harness.py), [src/eval/scoring.py](src/eval/scoring.py), [src/eval/test_cases.py](src/eval/test_cases.py)

## CI / GitHub Actions

- The repository includes a workflow at `.github/workflows/eval.yml` that runs the evaluation harness on `push`/`pull_request` to `main`. It:
  - Checks out the repo, sets up Python, installs dependencies, runs `python main.py eval` with `GROQ_API_KEY` supplied from repository secrets, uploads `eval_report.json` and `eval_report.md` as artifacts, and appends the Markdown report to the job summary.
- To enable the workflow, add the `GROQ_API_KEY` secret in the repository settings: *Settings → Secrets and variables → Actions → New repository secret*.

## Environment variables

- `GROQ_API_KEY` (required for evals and LLM judge calls)
- `MODEL_NAME` (optional; defaults provided in `src/config.py`)
- `TEMPERATURE` and `SEED` (controls determinism)
- `CHROMA_PERSIST_DIR` (optional: path for chroma DB)

Add these to a local `.env` file for development (do not commit your real API keys). Example `.env`:

```dotenv
GROQ_API_KEY=sk-<your-key>
MODEL_NAME=llama-3.1-70b-versatile
TEMPERATURE=0
SEED=42
```

## Local development checklist

1. Create virtualenv and install deps:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Build the RAG index (required before serving or running evals):

```bash
python main.py index --force
```

3. Run unit manual checks:

```bash
# Run the eval harness (requires GROQ_API_KEY)
export GROQ_API_KEY="<your_key>"
python main.py eval

# Start API server
python main.py serve

# Start Streamlit UI (optional)
python main.py ui
```

## Debugging tips

- If evaluations fail with LLM errors, confirm `GROQ_API_KEY` is set and valid.
- Check `chroma_db/` for a valid `chroma.sqlite3` after indexing.
- Look at the uploaded artifacts in CI runs for the `eval_report.json` to see detailed failures.

## Where to look next (quick tour)

- Read the prompts and prompt registry: `src/triage/prompts.py` and `src/summariser/prompts.py` to understand the exact LLM instructions.
- Inspect the evaluation test definitions: `src/eval/test_cases.py` to see acceptance criteria and adversarial tests.
- See `src/rag/indexer.py` for how KB files are chunked and embedded.

---

If you want I can:
- add `workflow_dispatch` to `.github/workflows/eval.yml` to allow manual runs,
- expand this script into slides or a spoken script for a Loom recording,
- or generate a concise 2–3 minute verbal script you can read while recording.

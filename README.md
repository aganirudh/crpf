# PRAMAAN

**P**rocurement **R**eview, **A**djudication & **M**achine-**A**ssisted **A**udit **N**etwork

> An AI platform for the Central Reserve Police Force (CRPF) that turns a tender + a stack of bidder submissions into a signed, click-traceable, criterion-by-criterion eligibility report — with **zero LLM-driven verdicts** and a **cryptographic audit trail** end to end.

This repository is the Round 1 written submission **plus** the Round 2 MVP scaffold for **Theme 3: AI-Based Tender Evaluation and Eligibility Analysis for Government Procurement by CRPF**.

---

## The pitch in one sentence

> **LLMs read. Symbolic logic decides. Cryptography proves. Humans approve.**

PRAMAAN never lets a language model say "Eligible" or "Not Eligible." LLMs and vision models only **extract** structured evidence from documents. A deterministic **Open Policy Agent (Rego)** rules engine adjudicates. Every value is grounded to a `(document, page, bbox)` and every verdict is hash-chained and signed so the same inputs always produce a byte-identical, reproducible report.

---

## Round 1 — Read the design first

Read in order. Each document is self-contained but they build on each other.

| # | Document | What it covers |
|---|---|---|
| 0 | [`README.md`](README.md) | You are here |
| 1 | [`docs/01-solution.md`](docs/01-solution.md) | **Master solution document** — the one to read if you read only one |
| 2 | [`docs/02-architecture.md`](docs/02-architecture.md) | Full system architecture with diagrams (system, sequence, agent topology, data flow) |
| 3 | [`docs/03-criterion-dsl.md`](docs/03-criterion-dsl.md) | The typed Criterion DSL — the contract between LLM extraction and symbolic adjudication |
| 4 | [`docs/04-document-pipeline.md`](docs/04-document-pipeline.md) | OCR + VLM + layout parsing for typed PDFs, scans, photos, stamps, handwriting |
| 5 | [`docs/05-adjudication.md`](docs/05-adjudication.md) | The neuro-symbolic adjudicator, the Skeptic agent, and the abstention policy |
| 6 | [`docs/06-audit-ledger.md`](docs/06-audit-ledger.md) | Merkle-chained event log, signed report bundles, reproducibility |
| 7 | [`docs/07-officer-ux.md`](docs/07-officer-ux.md) | Procurement officer split-pane reviewer, override workflow, sign-off |
| 8 | [`docs/08-integrity-layer.md`](docs/08-integrity-layer.md) | **Bonus** — cross-bidder collusion / cartel / forgery detection |
| 9 | [`docs/09-stack-rationale.md`](docs/09-stack-rationale.md) | Every model and tool choice with rejected alternatives |
| 10 | [`docs/10-risks-tradeoffs.md`](docs/10-risks-tradeoffs.md) | Honest failure modes and how we mitigate them |
| 11 | [`docs/11-round2-roadmap.md`](docs/11-round2-roadmap.md) | Week-by-week Round 2 sandbox build plan |
| A | [`docs/appendix-sample-io.md`](docs/appendix-sample-io.md) | The brief's 4-criterion construction tender, walked end-to-end through the system |

---

## The five pillars (the differentiators)

1. **Sovereign by default** — air-gapped, on-prem, open-weights. Tender data never leaves CRPF's network.
2. **Neuro-symbolic adjudication** — LLMs extract typed evidence; **Open Policy Agent (Rego)** delivers the verdict. The decision is code, not a vibe.
3. **Pixel-grounded evidence graph** — every extracted value carries `(doc_hash, page, bbox, ocr_conf, model_version)`. Click any cell in the report → jump to the highlighted region in the source PDF.
4. **Multi-agent adversarial verification** — a **Skeptic** agent must fail to overturn each verdict before it is finalized. Otherwise the case is escalated to Manual Review.
5. **Cryptographic audit ledger** — every event is appended to a hash-chained log. Every final report is a signed bundle pinning model, prompt, and rule versions. Re-run = byte-identical output.

Plus a bonus: an **Integrity Layer** that surfaces cartel / collusion / forgery signals across the *set* of bidders — something no generic LLM-wrapper submission will have.

---

## Round 2 — The MVP build

### Repo layout

```
crpf/
├── README.md                  ← you are here
├── docs/                      ← Round 1 written submission
├── backend/                   ← FastAPI + SQLAlchemy + LLM agents
│   ├── pramaan/
│   │   ├── main.py            ← FastAPI entry
│   │   ├── config.py          ← pydantic-settings env
│   │   ├── db/                ← models, session, base
│   │   ├── dsl/               ← CriterionDSL types
│   │   ├── llm/               ← OpenAI-compatible client (swappable)
│   │   ├── ingestion/         ← document classifier + OCR + layout
│   │   ├── agents/            ← Cartographer, Excavator (W3), …
│   │   ├── ledger/            ← hash-chained audit log
│   │   ├── storage/           ← MinIO blob store
│   │   ├── routers/           ← FastAPI HTTP routes
│   │   ├── prompts/           ← versioned prompt templates
│   │   └── scripts/           ← CLI entry points (db_reset, ledger_verify, …)
│   ├── policies/              ← Rego (W4)
│   ├── tests/
│   ├── alembic/
│   └── pyproject.toml         ← uv-managed
├── frontend/                  ← Next.js 15 + Tailwind v4 + shadcn/ui
│   ├── app/                   ← App Router pages
│   ├── components/            ← UI primitives + providers
│   └── lib/                   ← typed API client
├── infra/
│   ├── docker-compose.yml     ← Postgres + MinIO + Qdrant + OPA
│   └── postgres/init.sql
├── scripts/
│   └── pramaan_colab_vllm.ipynb   ← run an open-weights LLM on free Colab
├── samples/                   ← demo tender + bidders go here
└── Makefile
```

### Tech stack

| Layer | Choice | Why |
|---|---|---|
| Backend | Python 3.12 + FastAPI + SQLAlchemy 2.x | Best ML/OCR ecosystem; typed I/O |
| Package manager | **uv** | Fast; lockfile-based; modern |
| DB | Postgres 16 + JSONB + (optional) pgvector | One DB, three workloads |
| Object store | MinIO (S3-compatible) | Self-hostable; content-addressed keys |
| Vector store | Qdrant | Self-hostable; payload filtering |
| Rules engine | Open Policy Agent (Rego) | Declarative, auditable, battle-tested |
| OCR | Tesseract (dev) → PaddleOCR + docTR (prod) | Indic script support |
| LLM extractor | OpenAI-compatible client (provider-agnostic) | Swappable: OpenAI, OpenRouter, Groq, Together, Ollama, Colab vLLM |
| Frontend | Next.js 15 + TS + Tailwind v4 + shadcn/ui + react-pdf | Modern; bbox-overlay-friendly |
| Auth | OIDC-ready (mock for dev) | NIC SSO / e-Pramaan compatible |

Full justifications and rejected alternatives in [`docs/09-stack-rationale.md`](docs/09-stack-rationale.md).

---

## Quickstart

### Prerequisites

- Python 3.12, **uv** (`pip install uv` or `winget install astral-sh.uv`)
- Node 20+ and npm
- Docker Desktop (for Postgres + MinIO + Qdrant + OPA)
- Tesseract OCR — Windows: [UB-Mannheim build](https://github.com/UB-Mannheim/tesseract/wiki); macOS: `brew install tesseract`; Linux: `apt install tesseract-ocr`

### One-time setup

```powershell
# 1. Copy env file and pick an LLM provider
copy .env.example .env

# 2. Install backend + frontend deps
make install            # runs uv sync + npm install

# 3. Boot infra (Postgres, MinIO, Qdrant, OPA)
make infra-up

# 4. Apply migrations
make db-migrate
```

### LLM providers (pick one)

The LLM client speaks the OpenAI Chat Completions schema, so any compatible endpoint works. In `.env`, set:

| Provider | `PRAMAAN_LLM_BASE_URL` | Notes |
|---|---|---|
| OpenAI | `https://api.openai.com/v1` | Easiest |
| OpenRouter | `https://openrouter.ai/api/v1` | Free / cheap open-weights (Llama, Qwen) |
| Groq | `https://api.groq.com/openai/v1` | Very fast Llama 3 inference |
| Together.ai | `https://api.together.xyz/v1` | Wide model selection |
| Local Ollama | `http://localhost:11434/v1` | Fully local; needs GPU + RAM |
| **Colab vLLM** | `https://<your-ngrok>.ngrok-free.app/v1` | **No GPU on your machine? Open `scripts/pramaan_colab_vllm.ipynb` in Google Colab; it serves Qwen 2.5 7B over an ngrok tunnel.** |
| (Fully offline) | leave `PRAMAAN_LLM_API_KEY` blank | Falls back to deterministic mock — useful for tests |

### Run

```powershell
# Two terminals:
make backend    # uvicorn on :8000
make frontend   # next on :3000
```

Open http://localhost:3000.

### What works today (as of W2 of the Round 2 roadmap)

- ✅ Upload tender PDF
- ✅ Cartographer agent extracts CriterionDSL via LLM (with structured-output enforcement)
- ✅ Officer reviews / edits / locks the criteria
- ✅ Hash-chained audit ledger captures every step
- ✅ MinIO content-addressed storage
- ✅ Bidder + document upload endpoints (frontend ingest UI lands with W3)

### What's coming (W3–W6)

See [`docs/11-round2-roadmap.md`](docs/11-round2-roadmap.md) for the week-by-week plan.

- **W3** — Excavator agent + Evidence Graph
- **W4** — Adjudicator (OPA Rego) + Skeptic + abstention policy
- **W5** — Officer split-pane UX + override workflow
- **W6** — Audit ledger sealing + Integrity Layer + signed export

---

## Useful commands

```powershell
make help              # list all targets
make infra-up          # start docker compose
make infra-logs        # tail logs
make db-migrate        # apply migrations
make db-reset          # dev-only: drop + recreate + migrate
make backend           # run FastAPI dev server
make frontend          # run Next.js dev server
make test              # pytest
make lint              # ruff check
make format            # ruff format
make ledger-verify     # verify the hash chain
```

---

## Status

- **Round 1**: Complete — `docs/`
- **Round 2 W1–W2**: Complete — backend foundation, ingestion pipeline, Cartographer agent, tender + DSL screens, audit ledger
- **Round 2 W3+**: In progress — see roadmap

# Round 2 Implementation Roadmap

A six-week build that ends in a demo of the brief's exact scenario. Every week ends with something runnable.

This roadmap is the source of truth for what we build. It maps directly onto the architecture in `02-architecture.md`.

---

## Repository layout (locked at W1)

```
crpf/
├── README.md
├── docs/                          # Round 1 submission (this folder)
├── backend/
│   ├── pramaan/
│   │   ├── __init__.py
│   │   ├── main.py                # FastAPI entry
│   │   ├── config.py
│   │   ├── deps.py
│   │   ├── db/                    # Postgres / Alembic / models
│   │   ├── dsl/                   # CriterionDSL types + compiler-to-Rego
│   │   ├── ingestion/             # router, OCR, VLM, layout, normalizer
│   │   ├── agents/
│   │   │   ├── cartographer.py
│   │   │   ├── excavator.py
│   │   │   ├── adjudicator.py     # OPA wrapper
│   │   │   ├── skeptic.py
│   │   │   ├── scribe.py
│   │   │   └── integrity.py
│   │   ├── ledger/                # hash-chain, signing, replay
│   │   ├── routers/               # FastAPI HTTP routes
│   │   └── prompts/               # versioned prompt templates
│   ├── policies/                  # generated Rego files + handwritten core
│   ├── tests/
│   │   └── golden/                # golden bundles for CI replay
│   ├── alembic/
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/
│   ├── app/                       # Next.js App Router pages
│   ├── components/
│   ├── lib/
│   ├── package.json
│   └── Dockerfile
├── infra/
│   ├── docker-compose.yml         # sandbox profile
│   └── helm/                      # production air-gap chart
├── samples/                       # mock tenders + bidders for demo
├── scripts/
│   ├── pramaan-cli.py             # ledger verify, replay, etc.
│   └── seed-demo.py
├── Makefile
└── .env.example
```

---

## Week 1 — Ingestion and provenance

**Goal:** any document in, an `EvidenceNode` list out, with provenance.

- Repo scaffold (backend + frontend + infra + Makefile)
- `docker-compose.yml` with Postgres 16, MinIO, Qdrant, Redis, Langfuse
- FastAPI skeleton with `/health` and `/upload`
- Document classifier (typed-pdf / scanned-pdf / photo / docx / xlsx)
- OCR pipeline: PaddleOCR primary, docTR fallback, Tesseract last resort
- VLM pipeline: Qwen2.5-VL-7B served via vLLM (or use a hosted Qwen-VL endpoint behind a feature flag if no GPU available locally)
- Layout: pdfplumber + table-transformer
- Provenance tagger: every extracted span carries `(doc_sha256, page, bbox, ocr_conf, model_version)`
- Postgres schema (`tender`, `bidder`, `document`, `evidence_node`)
- CI: `pytest` smoke test that ingests a sample PDF and asserts at least N nodes with bboxes

**End-of-week demo:** drop a PDF into the API, get back a JSON of evidence nodes with bboxes.

---

## Week 2 — Cartographer + CriterionDSL

**Goal:** tender PDF → typed CriterionDSL → editable in UI.

- CriterionDSL Pydantic schema (matching `03-criterion-dsl.md`)
- Cartographer agent: prompt + Outlines/Instructor structured output against Llama-3.1-70B (vLLM) or, if no GPU, a hosted model behind a feature flag
- Mandatoriness classifier with confidence
- Compile-to-Rego module skeleton (just for the four criterion types in the brief: financial / technical / compliance / certification)
- DSL persisted to Postgres
- Frontend: Next.js scaffold + shadcn/ui + first screen (Tender intake) + DSL review screen with editable cards
- CI: a small library of mock tender extracts → expected DSL outputs

**End-of-week demo:** upload `samples/tender_construction_2026.pdf`, see the four criteria as cards, edit one, lock.

---

## Week 3 — Excavator + Evidence Graph

**Goal:** bidder bundle → fully populated EvidenceGraph → visible in UI.

- Excavator agent: orchestrates the W1 pipeline per document and emits typed evidence nodes
- Field extractor with `source_quote` enforcement and bbox-realignment
- Indian-numbering + date + entity normalizer
- Cross-document agreement scoring per field
- Frontend: Bidder intake screen with progress per document
- CI: golden bidder bundles → expected evidence graphs

**End-of-week demo:** upload three bidder bundles (one all-typed, one with scans, one with a photo of a certificate), see the evidence graph for each.

---

## Week 4 — Adjudicator (OPA / Rego) + Skeptic + Abstention

**Goal:** verdicts on the 4 criteria for the 10 bidders, including the amber case.

- DSL → Rego compiler for all four criterion types in the brief
- OPA sidecar in `docker-compose.yml`
- Adjudicator service: pure Python wrapper that calls OPA and captures decision traces
- Skeptic agent: adversarial prompt; uses the same vLLM
- Abstention policy as code: all 9 triggers from `05-adjudication.md`
- External validators: stub implementations that return `{verified|inconclusive}` based on a local fixture (real GST/UDIN APIs deferred to W6)
- Frontend: the report grid (left pane) with color-coded cells

**End-of-week demo:** upload tender + 10 bidders, see the 6/3/1 verdict matrix, click a cell, see the verdict drawer.

---

## Week 5 — Officer UX (split-pane + overrides)

**Goal:** the demo screen the brief describes, end-to-end usable.

- `react-pdf` viewer in the right pane with custom bbox-overlay layer
- Click cell → jump to source page with bbox highlighted
- Verdict drawer with full reasoning, evidence list, suggested action
- Override dialog with controlled-vocabulary tag + reason text
- Per-criterion re-evaluation API (so a freshly uploaded scan can re-run *just* C1)
- OIDC auth scaffold (mock provider for demo)
- Frontend polish: loading states, error states, empty states

**End-of-week demo:** click amber cell → see scan with bbox → upload clearer scan → cell turns green.

---

## Week 6 — Audit ledger + Integrity Layer + signed export

**Goal:** evaluation that survives audit, plus the Integrity Layer wow.

- `ledger_event` table, hash chain, append-only DB role
- All agent transitions write events to the ledger
- `pramaan ledger verify` CLI
- Scribe service: assembles the `ReportBundle`, signs via SoftHSM
- Export as PDF + `.pramaan` archive (tar.gz with verify.sh)
- CI: golden bundles re-played → byte-identical
- Integrity Engine: shared director / address / phone / bid-price clustering / near-duplicate document detection (using mock data)
- Frontend: Integrity Panel + Linkage Graph (vis-network)
- Demo polish + scripted demo flow

**End-of-week demo:** the brief's full scenario, end-to-end, signed and exported.

---

## Cut-list (what we will *not* build in 6 weeks, by design)

- Real GST / MCA21 / UDIN / ISO accreditation API integrations (use stub validators in MVP)
- Production HSM (SoftHSM only)
- Multi-tenancy (single CRPF tenant)
- Hindi UI (English only; tender text shown in original language)
- Bidder-portal (officers upload on bidders' behalf)
- Helm air-gap chart (sandbox docker-compose only)
- Active-learning loop for officer corrections feeding back into extraction
- Long-term retention / archival
- Mobile-friendly UI

These are explicitly post-MVP.

---

## Definition of done for the demo

By end of W6 we can do this in front of a CRPF judge:

1. Upload `tender_construction_2026.pdf`. Wait ~60 seconds. Confirm extracted criteria.
2. Upload 10 bidder folders (one zip per bidder, mixing typed PDFs, scans, and a few photographed certificates). Wait ~5–10 minutes.
3. Show the report: 6 green, 3 red, 1 amber.
4. Click a red bidder's failed criterion → right pane shows the page where the figure proves the criterion fails.
5. Click the amber bidder's turnover → right pane shows the fuzzy scan; verdict drawer shows the reason and a suggested action.
6. Upload a clearer scan; click "Re-evaluate C1"; bidder turns green.
7. Open the Integrity Panel: two bidders flagged for shared director; one bidder flagged for ISO certificate not in registry.
8. Click "Sign and Export." Enter signing PIN. Download the signed PDF and `.pramaan` archive.
9. Run `pramaan ledger verify --tender ...` in the terminal → "OK (chain intact)."
10. Run `pramaan replay --bundle report.pramaan` → byte-identical bundle.

That is the bar.

---

## Risks to the schedule

- GPU availability for the 70B model. Mitigation: feature-flag a pilot-profile fallback to a hosted API for the demo, while the production path stays open-weights.
- vLLM determinism: minor work to ensure `seed`+`temperature=0` produces stable outputs across our pipeline. Mitigation: golden tests in CI from W1.
- VLM accuracy on the photographed-certificate edge case. Mitigation: prep the demo's photo to be readable; show what *Manual Review* looks like for unreadable cases (which is the actual point — never silently fail).

---

## What happens after Round 2

If selected for further development, immediate priorities are:

1. Real validator integrations (GSTN, MCA21, ICAI UDIN, ISO accreditation).
2. Helm chart with air-gap profile + Helm OCI registry.
3. HSM integration (YubiHSM / NIC equivalent).
4. Active-learning loop: officer overrides feed an evaluation set that drives prompt and policy improvements.
5. Pilot deployment behind a CRPF firewall.

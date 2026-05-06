# Stack and Tooling Rationale

For each layer of PRAMAAN, this document records the chosen tool, the alternatives considered, and the reason the alternatives were rejected. The decisions are biased toward open-source, self-hostable, sovereign-deployable, and audit-friendly choices — in that order.

---

## 1. Backend language and framework

**Choice:** Python 3.12 + FastAPI

**Alternatives considered and rejected:**

| Alternative | Reason rejected |
|---|---|
| Node.js / Express / NestJS | Python's ML/OCR/document-AI ecosystem is dominant; we'd be in `python-shell` calls constantly |
| Go (Fiber / Echo) | Same reason; also LLM client libraries are weakest here |
| Java / Spring | Heavier; less idiomatic for ML; longer iteration cycles |

**Why FastAPI specifically:** native async, OpenAPI generation, Pydantic-typed I/O matches our DSL/EvidenceGraph design, easy WebSocket support for streaming agent updates to the UI.

---

## 2. Frontend

**Choice:** Next.js 15 (App Router) + TypeScript + shadcn/ui + react-pdf

**Alternatives considered and rejected:**

| Alternative | Reason rejected |
|---|---|
| Plain React + Vite | Loses SSR; harder to handle the "report initial render" performantly |
| SvelteKit | Smaller component ecosystem; shadcn-equivalents weaker |
| Streamlit / Gradio | Adequate for prototype, fails for officer-grade UX |
| Material UI / Ant Design | Less themable; larger bundle; we want a govt-friendly clean look |

**Why react-pdf specifically:** mature pdf.js wrapper, supports custom annotation/overlay layers (essential for our bbox highlighting), no proprietary lock-in.

---

## 3. OCR

**Choice:** PaddleOCR (primary) + docTR (fallback) + Tesseract (last resort) + TrOCR (handwriting)

**Alternatives considered and rejected:**

| Alternative | Reason rejected |
|---|---|
| AWS Textract / Google Document AI / Azure Form Recognizer | Hosted; sovereignty fail |
| EasyOCR | Underperforms PaddleOCR on Indic scripts |
| Mathpix / Adobe Extract | Hosted; pricing not feasible at scale |

**Why this stack:** PaddleOCR is the only open-source OCR with first-class support for Indian languages. docTR provides excellent confidence scores. Tesseract is the universal fallback. TrOCR handles handwritten endorsements common on Indian government certificates.

---

## 4. Vision-language model (for stamps, photos, seals)

**Choice:** Qwen2.5-VL-7B (Apache 2.0)

**Alternatives considered and rejected:**

| Alternative | Reason rejected |
|---|---|
| GPT-4V / Claude 3 Vision / Gemini | Hosted; sovereignty fail |
| LLaVA-1.6 | Older; weaker on documents |
| InternVL2 | Strong alternative; we keep it as a swap-in |
| MiniCPM-V | Lighter but weaker on dense text |

**Why Qwen2.5-VL-7B:** Apache 2.0 license, strong document understanding benchmarks, 7B fits on a single L4/A10G, supports structured JSON output natively, multilingual including Indic.

---

## 5. Layout / table extraction

**Choice:** LayoutLMv3 + table-transformer + Nougat

**Alternatives considered and rejected:**

| Alternative | Reason rejected |
|---|---|
| Camelot / Tabula | OK for clean PDFs; fails on scanned and complex layouts |
| GROBID | Optimized for scientific papers, not procurement docs |
| Adobe Extract | Hosted |
| Donut | Strong end-to-end but harder to retrieve bboxes from |

**Why this stack:** different engines for different layout classes. We score and pick the best output per page.

---

## 6. LLM extractor (the Cartographer + Excavator)

**Choice:** Llama-3.1-70B-Instruct OR Qwen2.5-72B served via vLLM

**Alternatives considered and rejected:**

| Alternative | Reason rejected |
|---|---|
| GPT-4o / Claude 3.5 Sonnet / Gemini 1.5 | Hosted; sovereignty fail; only allowed in pilot profile for benchmarking |
| Llama-3.1-8B / Mistral 7B | Insufficient for structured extraction at this complexity |
| Mixtral 8x22B | Strong but VRAM-heavier; slower per-token |
| Self-hosted GPT-style finetune | Too much custom work for MVP; revisit after we have ground-truth data |

**Why two options:** Llama-3.1-70B is the safest open-weights default; Qwen2.5-72B has a slight edge on document-extraction benchmarks and on Hindi. Both are swappable through the same vLLM server.

**Why vLLM specifically:**

| Alternative | Reason rejected |
|---|---|
| Hugging Face TGI | Slower throughput; less mature in production |
| llama.cpp / Ollama | CPU-friendly but weaker GPU throughput; less suited for batching |
| TensorRT-LLM | Faster but NVIDIA-only and heavier ops burden |

vLLM gives us PagedAttention, continuous batching, deterministic seeding, and is the de facto open-source serving standard.

---

## 7. Structured output enforcement

**Choice:** Outlines OR Instructor

**Alternatives considered and rejected:**

| Alternative | Reason rejected |
|---|---|
| JSON-mode with retry-on-parse | Not reliable enough; lets the model emit invalid JSON, costs tokens |
| Manual JSON-schema prompts | Same problem; depends on the model's discipline |
| Guardrails AI | Heavier; we don't need its full validation framework |

Outlines does **constrained decoding** at the token level — the model literally cannot emit a token that violates the schema. Instructor wraps this for the Python SDK side. This is critical: our DSL contract must hold every time.

---

## 8. Rules engine

**Choice:** Open Policy Agent (Rego)

**Alternatives considered and rejected:**

| Alternative | Reason rejected |
|---|---|
| Drools | JVM weight; Java integration tax |
| Datalog (Soufflé / pyDatalog) | Underpowered for typed scalar comparisons; weak ecosystem |
| Cedar (AWS) | Newer; designed for authz; smaller community |
| Hand-written Python rules | Defeats the audit-friendliness purpose |
| Decision tables (DMN) | Adequate but with weaker tooling than OPA |

OPA is mature, declarative, has battle-tested production usage in Kubernetes and Terraform, has `conftest` for unit tests, has `--explain=full` for decision tracing. The decision trace is what we put in the audit ledger.

---

## 9. Vector store

**Choice:** Qdrant

**Alternatives considered and rejected:**

| Alternative | Reason rejected |
|---|---|
| Pinecone / Weaviate Cloud | Hosted; sovereignty fail |
| Chroma | Adequate for prototype; weaker at scale and metadata filtering |
| Milvus | More operational overhead than we need at MVP scale |
| pgvector alone | We use pgvector for one purpose (embedding fields on `evidence_node`), but Qdrant wins for the corpus-search use case |

Qdrant has strong payload filtering, on-prem deployment, and per-collection tenancy.

---

## 10. Primary data store and ledger

**Choice:** Postgres 16 + JSONB + pgvector + (optional) immudb

**Alternatives considered and rejected:**

| Alternative | Reason rejected |
|---|---|
| MongoDB | We want strong relational guarantees + JSONB; PG gives both |
| MySQL / MariaDB | Weaker JSONB and partitioning than PG |
| Append-only log database (e.g. Datomic) | Niche; smaller ecosystem; not friendly to govt ops teams |

The audit ledger lives in Postgres with append-only DB privileges and a hash chain. For high-trust deployments, `immudb` provides cryptographic database-tampering protection on top.

---

## 11. Orchestration / agent runtime

**Choice:** Custom finite-state-machine in Python

**Alternatives considered and rejected:**

| Alternative | Reason rejected |
|---|---|
| LangGraph | Hides too much for an audit context; checkpointer not byte-reproducible across versions |
| LangChain Agents | Magic-heavy; hard to inspect; verdict-path opacity |
| Llama Index Workflows | Same concerns; oriented to RAG |
| Temporal | Overkill for our scale; ops-heavy |
| Prefect / Dagster | Built for data pipelines, not agent orchestration |

A 5-state FSM in a single Python file is trivially auditable. Every transition logs to the ledger. This is what we want.

---

## 12. LLM observability

**Choice:** Langfuse (self-hosted)

**Alternatives considered and rejected:**

| Alternative | Reason rejected |
|---|---|
| Helicone / LangSmith | Hosted; sovereignty fail |
| Phoenix (Arize) | Strong alternative; we may swap to it; Langfuse won on simpler self-hosting |
| Custom OTel-only | Loses LLM-specific UX (prompt diff, eval views) |

Langfuse self-hosts cleanly, captures prompt + completion + cost + latency per call, and makes it easy to compare prompt versions side-by-side.

---

## 13. Auth

**Choice:** OIDC, designed to plug into NIC SSO / e-Pramaan

**Alternatives considered and rejected:**

| Alternative | Reason rejected |
|---|---|
| Custom username/password | No, please |
| SAML | Older; OIDC is the modern path; we keep SAML compatibility as a bridge |
| Auth0 / Okta SaaS | Hosted; sovereignty fail |

OIDC is modern, standards-based, and integrates with the Indian government's identity infrastructure.

---

## 14. Deployment

**Choice:** Docker Compose (sandbox) → Helm chart with air-gap profile (production)

**Alternatives considered and rejected:**

| Alternative | Reason rejected |
|---|---|
| Bare metal scripts | Reproducibility nightmare |
| Ansible-only | Adequate for VMs but not for a dozen services |
| Nomad | Lighter than K8s but smaller ecosystem in govt deployments |
| Cloud-managed K8s | OK for the pilot profile; production must support fully air-gapped |

Helm is the standard and supports offline-installable charts.

---

## 15. CI / CD

**Choice:** GitHub Actions (dev) + Drone or Gitea Actions (sovereign mirror)

We assume the actual CRPF deployment will use a sovereign Git/CI mirror; our build artifacts are designed to be portable.

---

## 16. Secret and key management

**Choice:** SoftHSM (dev) + YubiHSM/CloudHSM-equivalent (prod) for signing keys; Vault for application secrets

The signing key never leaves the HSM. Application secrets (DB credentials, model API keys for the pilot profile) are read from Vault.

---

## 17. Why this stack overall

Every choice above passes three filters:

1. **Sovereignty.** Everything can run air-gapped on CRPF infrastructure.
2. **Auditability.** Every component emits inspectable traces / logs / hashes.
3. **Maturity.** Nothing in production depends on a one-person GitHub project.

The stack is deliberately conservative on infrastructure (Postgres, Redis, MinIO, Helm, OPA — all boring, battle-tested) and deliberately ambitious where it must be (the agent topology, the DSL, the verifiable bundle).

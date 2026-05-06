# Audit Ledger and Reproducibility

The brief lists auditability as a non-negotiable. PRAMAAN treats it as the system's spine. Every state change is an event. Every event is hashed and chained. Every report is a signed bundle. Every evaluation is byte-identically reproducible.

This document specifies how.

---

## 1. The threat model

We design against three classes of threat:

1. **Insider tampering.** A privileged user attempts to alter past evaluations to bias a procurement decision.
2. **External challenge.** A losing bidder challenges the result via the CVC / GFR appeal process and demands proof that the evaluation was correctly conducted.
3. **Replay drift.** Models change, prompts change, code changes — and a re-run of a past evaluation no longer matches the original.

The audit ledger and the signed report bundle defend against all three.

---

## 2. The hash-chained event log

Every event is appended to the `ledger_event` table. Each event includes the hash of the previous event. Tampering with any past event invalidates the hash chain from that point forward, which is detectable in O(n) by re-hashing.

```
event_n.payload   = canonical_json(event_n_data)   # RFC 8785 JCS
event_n.prev_hash = event_{n-1}.hash
event_n.hash      = sha256(event_n.payload || event_n.prev_hash)
```

We use **canonical JSON** (RFC 8785) so that hashes are stable across language runtimes and key orderings.

### 2.1 What gets logged

| Event kind | When | Payload |
|---|---|---|
| `tender.uploaded` | Officer uploads tender | `{tender_sha256, filename, officer_id, ts}` |
| `bidder.uploaded` | Officer uploads bidder bundle | `{bidder_id, doc_sha256s, officer_id, ts}` |
| `cartographer.run` | Cartographer extracts CriterionDSL | `{tender_id, dsl_sha256, model, prompt_hash, run_id, ts}` |
| `dsl.confirmed` | Officer confirms / edits DSL | `{tender_id, dsl_sha256, dsl_diff, officer_id, ts}` |
| `excavator.run` | Excavator extracts evidence | `{bidder_id, evidence_graph_sha256, model, prompt_hash, run_id, ts}` |
| `validator.call` | External validator invoked | `{validator, input, response, latency_ms, ts}` |
| `adjudicator.eval` | OPA evaluates a criterion | `{bidder_id, criterion_id, opa_input_sha256, opa_output_sha256, policy_hash, opa_version, ts}` |
| `skeptic.review` | Skeptic produces accept/counter | `{bidder_id, criterion_id, outcome, counter, prompt_hash, ts}` |
| `verdict.final` | Final verdict committed | full `Verdict` object |
| `officer.override` | Officer overrides a verdict | `{verdict_id, new_status, reason, reason_tag, officer_id, ts}` |
| `report.signed` | Final signed bundle produced | `{report_sha256, signature, signer_id, ts}` |
| `report.exported` | Officer downloads the bundle | `{report_id, officer_id, ts}` |

### 2.2 Append-only enforcement

At the database level, the application's role has only `INSERT` privilege on `ledger_event`. `UPDATE` and `DELETE` are revoked. Even a privileged DBA action would leave forensic traces in PostgreSQL's WAL.

For high-trust deployments we additionally back the ledger with [`immudb`](https://github.com/codenotary/immudb), which provides cryptographic verification that the database has not been tampered with — including by anyone with full DB access.

### 2.3 Verifying the chain

A `pramaan ledger verify` CLI re-hashes every event and confirms the chain is intact. CI runs this on every release. The officer can run it from the UI for any tender.

```bash
$ pramaan ledger verify --tender T-CRPF-2026-CONST-014
Verifying 1,847 events...  OK (chain intact, hash sha256:f8a2...)
```

---

## 3. The signed report bundle

When the officer signs off, the Scribe assembles a `ReportBundle`:

```json
{
  "version": "v1",
  "tender": {
    "id": "T-CRPF-2026-CONST-014",
    "sha256": "e3a1c4...",
    "filename": "tender_construction_2026.pdf"
  },
  "bidders": [
    {
      "id": "b_07",
      "legal_name": "ABC Constructions Pvt. Ltd.",
      "cin": "U45200DL2015PTC123456",
      "documents": [
        {"filename": "audited_fs_2023_24.pdf", "sha256": "9f2b...", "pages": 42},
        {"filename": "ca_certificate.pdf", "sha256": "5d31...", "pages": 1}
      ]
    }
  ],
  "criterion_dsl": { ... full DSL ... },
  "criterion_dsl_sha256": "abc123...",
  "evidence_graphs": [ ... per bidder ... ],
  "verdicts": [ ... per bidder per criterion + overall ... ],
  "integrity_flags": [ ... ],
  "officer_overrides": [ ... ],
  "pinned_artifacts": {
    "extractor_model": {"name": "qwen2.5-72b@vllm", "weights_sha256": "..."},
    "vlm_model": {"name": "qwen2.5-vl-7b", "weights_sha256": "..."},
    "skeptic_model": {"name": "llama-3.1-70b@vllm", "weights_sha256": "..."},
    "ocr": {"paddleocr_version": "2.7.0", "doctr_version": "0.7.0"},
    "rego_policies": [
      {"module": "eligibility.C1", "sha256": "..."},
      ...
    ],
    "compiler_version": "1.0.3",
    "dsl_version": "v1",
    "opa_version": "0.65.0"
  },
  "ledger_root_hash": "sha256:f8a2...",  // hash of last ledger event for this tender
  "produced_at": "2026-04-22T11:53:00Z",
  "signed_by": {
    "officer_id": "officer:abc@crpf.gov.in",
    "officer_name": "Inspector A. B. Singh",
    "role": "evaluator-signer"
  },
  "signature": {
    "algo": "ECDSA-P256-SHA256",
    "key_id": "hsm:pramaan-prod-2026",
    "value": "MEUCIQ..."
  }
}
```

### 3.1 Signing

The signing key lives in an HSM. In dev that is SoftHSM; in production it is a hardware HSM (YubiHSM, AWS CloudHSM, or NIC-provided equivalent). The API service does not have direct access to the key. Only the Scribe service does, and only via a narrow `sign(bytes) -> signature` endpoint backed by the HSM.

Public keys are published in the bundle metadata and pinned at install time so a bidder's auditor can verify a bundle without contacting CRPF.

### 3.2 Export formats

The bundle is exported as:

- A single signed PDF (human-readable report with all evidence excerpts inline).
- A `.pramaan` archive (a tar.gz containing the JSON bundle, all source documents, all ledger events for the tender, and a `verify.sh` script).

The `.pramaan` archive is self-verifying: any third party with the published public key can run the script and confirm authenticity.

---

## 4. Reproducibility

The single most important property of the audit system: **the same inputs and the same pinned artifacts produce a byte-identical bundle**.

### 4.1 What we control

| Source of non-determinism | How we pin |
|---|---|
| LLM sampling | `temperature=0`, fixed `seed`, vLLM determinism flags |
| Prompt templates | Hashed and versioned |
| Model weights | SHA-256 pinned in artifact registry |
| OCR engine versions | Pinned in container image |
| Rego policies | Hashed; compiler version pinned |
| OPA version | Pinned |
| Time-dependent rules (e.g. "valid on today") | Bundle records the wall-clock time used; re-runs replay it |
| Random in retrieval / vector search | Fixed-seed deterministic re-rank |
| External validator responses | Recorded in the ledger; replayed on re-run unless explicitly refreshed |

### 4.2 Replay mode

`pramaan replay --bundle report.pramaan` re-evaluates the bundle's inputs against its pinned artifacts. The result must be a bundle whose hash equals the original (excluding the new signature, since the new run produces a new signature over the same content).

CI runs this on a corpus of golden bundles for every release. Any regression that breaks reproducibility fails the build. This is non-negotiable.

### 4.3 What replay does not control

We do not guarantee replay across:

- Different operating systems (we ship one container image, it is the only supported runtime).
- Different GPU vendors (deterministic CUDA only; we do not support other accelerators).
- Different versions of the system (each version's reproducibility is internal; cross-version replay requires an explicit migration tool).

These are stated up-front in the audit bundle metadata.

---

## 5. Officer overrides and the audit trail

Officer overrides are first-class events. The original verdict is **never deleted**. A typical override sequence in the ledger:

```
... event_127  verdict.final  bidder=b_03 criterion=C2 status=manual_review
... event_128  officer.override  verdict_id=v_127 new_status=eligible reason="Provided supplementary work-order copies via email; verified telephonically with project owner."
... event_129  report.signed
```

The signed bundle includes both the original Adjudicator output and the override. The PDF report shows the override prominently with the officer's name, time, reason, and tag.

This is by design: an auditor reviewing the bundle later sees not just the final verdicts but the entire history of how they were arrived at.

---

## 6. Privacy and retention

- Bidder PII is stored encrypted at rest (Postgres TDE / disk encryption) and in transit (mTLS).
- The ledger retains a rolling 7 years of events by default, configurable to match the procurement entity's policy (CRPF's retention is governed by GFR / CVC).
- Deletion is via a documented "redaction" event that records *what was redacted and why* without breaking the hash chain (the redacted payload is replaced by `sha256(original_payload)` so the hash chain remains intact and the existence-and-deletion are both provable).

---

## 7. What this enables

- A losing bidder appeals to the CVC. CRPF hands over the `.pramaan` bundle. The bidder's auditor verifies the signature, replays the evaluation, and either confirms the outcome or has a precise, evidence-grounded basis for the appeal.
- An internal auditor wants to spot-check ten random tenders from the last quarter. They run `pramaan ledger verify` and `pramaan replay` on each. The check is mechanical.
- A new procurement officer joins; their first override on any tender is logged, attributable, and reviewable.
- A model is updated. CI catches that the new model produces different outputs on the golden corpus. The team decides to either lock the new model out of production or document the model change as a versioned upgrade.

That is what auditability looks like when you take it seriously.

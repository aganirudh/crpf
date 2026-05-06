# The Criterion DSL

The **Criterion DSL** is the contract between the LLM extraction layer and the symbolic adjudication layer. It is the single most important abstraction in PRAMAAN. Get this right and everything downstream becomes correct, inspectable, and auditable.

---

## 1. Why a DSL at all?

Most "LLM-for-tenders" prototypes feed both the tender and the bidder docs into a single LLM and ask "is this bidder eligible?" That approach is unauditable. There is no machine-readable representation of *what was being checked*; the LLM's chain-of-thought is the only artifact, and it cannot be re-evaluated, re-played, or formally tested.

PRAMAAN forces the LLM to commit to a **typed, structured representation** of the criteria first. That representation:

- can be reviewed and edited by the procurement officer **before** any bidder is judged,
- can be compiled into Rego policies that a deterministic engine evaluates,
- can be unit-tested in CI,
- can be diffed across tenders to detect drift,
- and is the same representation used by the audit bundle.

This is the difference between "the LLM said so" and "the rule was X, the value was Y, the policy returned Z."

---

## 2. Top-level shape

A `CriterionDSL` document is a typed YAML/JSON document with three parts: tender metadata, a normalized criterion list, and an evidence-vocabulary glossary.

```yaml
tender:
  id: T-CRPF-2026-CONST-014
  source_sha256: e3a1c4...
  classification: construction_services
  language: en
  pages: 142
  extracted_by:
    model: qwen2.5-72b@vllm
    prompt_hash: cartographer:v3-2026-04-19
    run_id: 9f2b...
  reviewed_by: officer:abc@crpf.gov.in
  reviewed_at: 2026-04-22T11:34:00Z

criteria:
  - id: C1
    type: financial          # technical | financial | compliance | certification | documentary
    mandatory: true
    mandatory_confidence: 0.97
    text: "Minimum annual turnover of Rs. 5 crore in any of the last three financial years"
    text_source:
      page: 23
      bbox: [70, 410, 540, 462]
    constraint:
      field: annual_turnover_inr
      op: ">="
      value: 50000000
      window:
        last_n_fy: 3
        aggregator: any         # any | all | mean | best
    evidence_required:
      - audited_financial_statement
      - ca_certificate
    validators: [icai_udin_lookup]
    cross_check:
      - {against: itr, tolerance_pct: 5}
    notes: |
      Tender uses "shall have a minimum annual turnover" - mandatory language.
      Window is "any of the last three financial years" - aggregator = any.

evidence_vocabulary:
  audited_financial_statement:
    aliases: [audited financials, balance sheet, P&L statement]
    expected_fields: [annual_turnover_inr, fy, auditor_name, ca_membership_no]
  ca_certificate:
    aliases: [chartered accountant certificate, CA certificate, turnover certificate]
    expected_fields: [annual_turnover_inr, fy, ca_name, udin]
  gst_registration_certificate:
    aliases: [GST RC, GSTIN certificate, Form GST REG-06]
    expected_fields: [gstin, legal_name, registration_date, status]
```

The `evidence_vocabulary` is per-tender because tenders use different document names for the same artifact. The Cartographer enriches it as it reads the tender; the officer can edit it.

---

## 3. The criterion type taxonomy

| `type` | Meaning | Typical fields | Validators |
|---|---|---|---|
| `technical` | Capability or experience constraints | completed projects, equipment, engineer headcount, capacity | none / domain-specific |
| `financial` | Monetary thresholds | turnover, net worth, working capital, profit | UDIN, ICAI |
| `compliance` | Statutory registrations | GST, PAN, EPFO, ESIC, PF, labour licence | GSTN, EPFO, MCA21 |
| `certification` | Quality/process/product certs | ISO 9001/14001/27001, BIS, OEM authorization | accreditation body lookups |
| `documentary` | "Submit document X" with no further constraint | EMD receipt, undertaking, affidavit | format / signature checks |

Every criterion belongs to exactly one type. Type drives which validators are auto-attached and how the UI groups it.

---

## 4. The constraint grammar

Constraints are typed and small. The full grammar:

```
constraint     := scalar_constraint | set_constraint | doc_constraint
scalar_constraint :=
   field: <fieldname>
   op:    one of ">", ">=", "<", "<=", "==", "!=", "regex_match", "exists"
   value: <literal>
   window?: window_spec
   unit?:   <iso unit>

set_constraint :=
   field:   <fieldname>
   filter:  map<fieldname, filter_op>
   op:      "count >=" | "count ==" | "sum >=" | "max >=" | "min >=" | ...
   value:   <number>

doc_constraint :=
   field: <fieldname>
   op:    "exists" | "valid_on(<date>)" | "issued_after(<date>)"
   issuer?: <regex over issuer name>

window_spec :=
   last_n_fy?:    integer
   last_n_years?: integer
   between?:      [date, date]
   aggregator?:   "any" | "all" | "mean" | "max"
```

This grammar is intentionally minimal. If a tender expresses something the grammar cannot capture, the Cartographer must mark the criterion `escape_hatch: true` and provide a free-text constraint — these always route to Manual Review and can never be auto-evaluated. This is on purpose: we'd rather escalate than silently drop.

---

## 5. Mandatory vs optional — and the ambiguity zone

Tenders are written in legalese. The Cartographer classifies each criterion's mandatoriness using a four-bucket model:

| Linguistic cue | `mandatory` | `mandatory_confidence` |
|---|---|---|
| "shall", "must", "essential", "mandatory", "is required" | `true` | high (≥0.95) |
| "may", "optional", "if applicable" | `false` | high (≥0.95) |
| "should", "is expected to", "ought to" | `true` | medium (0.7–0.85) |
| "preferably", "desirable", "is an advantage" | `false` (with tag `preferred`) | medium (0.7–0.85) |
| Blank / ambiguous | `true` (conservative default) | low (≤0.6) |

A `mandatory_confidence` below 0.85 forces the **officer to confirm** the flag before adjudication runs. We never let the system silently treat "preferably ISO 9001" as either mandatory or optional.

---

## 6. Worked example — the brief's tender

```yaml
tender:
  id: T-CRPF-2026-CONST-014
  source_sha256: e3a1c4...
  classification: construction_services
  language: en
  pages: 142

criteria:
  - id: C1
    type: financial
    mandatory: true
    mandatory_confidence: 0.97
    text: "Minimum annual turnover of Rs. 5 crore"
    constraint:
      field: annual_turnover_inr
      op: ">="
      value: 50000000
      window: { last_n_fy: 3, aggregator: any }
    evidence_required: [audited_financial_statement, ca_certificate]
    validators: [icai_udin_lookup]
    cross_check:
      - {against: itr, tolerance_pct: 5}

  - id: C2
    type: technical
    mandatory: true
    mandatory_confidence: 0.96
    text: "At least 3 similar projects completed in the last 5 years"
    constraint:
      field: completed_projects
      filter:
        similarity_to_tender_scope: ">= 0.75"
        status: "completed"
        completion_date: ">= today - 5y"
      op: "count >="
      value: 3
    evidence_required: [completion_certificate, work_order]

  - id: C3
    type: compliance
    mandatory: true
    mandatory_confidence: 0.99
    text: "Valid GST registration"
    constraint:
      field: gstin
      op: "regex_match + active_on(today)"
      value: "^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]{3}$"
    evidence_required: [gst_registration_certificate]
    validators: [gstn_api_lookup]

  - id: C4
    type: certification
    mandatory: true
    mandatory_confidence: 0.94
    text: "ISO 9001 certification"
    constraint:
      field: iso_9001
      op: "exists + valid_on(today)"
    evidence_required: [iso_certificate]
    validators: [iso_accreditation_body_lookup]
```

This is what the LLM is **allowed** to produce. Outlines / Instructor enforces the schema; if the LLM tries to emit a free-text "criterion," the call fails and is retried with corrective feedback.

---

## 7. Compilation to Rego

Each criterion compiles to a Rego module. The compiler is a pure Python function with golden tests. Example for `C1`:

```rego
package eligibility.C1

default verdict := "manual_review"
default reason  := "no_evaluation"

# Pull evidence
turnover_nodes := input.evidence.financial.annual_turnover_inr_by_fy
ca_cert        := input.evidence.documents.ca_certificate

threshold := 50000000
today_year := time.year(time.now_ns())

# Restrict to the last 3 FYs
window_nodes := [n |
  n := turnover_nodes[_]
  fy_end := to_number(substring(n.fy, 5, 9))   # "2023-24" -> 2024
  today_year - fy_end <= 3
]

passing := [n |
  n := window_nodes[_]
  n.value >= threshold
  n.confidence >= 0.85
]

eligible {
  count(passing) >= 1
  ca_cert.exists
  ca_cert.udin_verified
}

ineligible {
  count(passing) == 0
  count(window_nodes) >= 1
  every n in window_nodes { n.confidence >= 0.85 }
}

verdict := "eligible"        { eligible }
verdict := "not_eligible"    { ineligible; not eligible }
verdict := "manual_review"   { not eligible; not ineligible }

reason := sprintf("All %d in-window FY turnovers are below %d", [count(window_nodes), threshold]) {
  ineligible
}
reason := "Turnover meets threshold; CA certificate UDIN verified" { eligible }
```

The Rego is *generated*, *versioned*, and *testable*. A library of golden tests (positive and negative cases) runs in CI for every change to the compiler.

---

## 8. Officer-side editing

The CriterionDSL is rendered in the UI as a friendly card per criterion with toggles for mandatory/optional, editable thresholds, and a side-by-side "tender quote that justified this" view (using `text_source.bbox`). The officer can:

- Toggle mandatory/optional
- Adjust thresholds
- Add a missing criterion
- Delete a hallucinated criterion

Every edit is recorded in the audit ledger as an `officer_dsl_edit` event and the diff is preserved. The adjudication run uses the **officer-confirmed** DSL, never the raw LLM output.

---

## 9. Versioning

The DSL itself is versioned (currently `v1`). Every CriterionDSL document carries `dsl_version: v1`. The compiler-to-Rego is versioned independently (`compiler_version: 1.0.3`). Both versions are pinned into the audit bundle so an old report can be re-evaluated tomorrow with bit-identical results.

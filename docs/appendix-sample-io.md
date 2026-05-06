# Appendix — Worked Sample (the brief's tender, end-to-end)

This appendix walks the brief's exact scenario through every stage of PRAMAAN. It exists to make the abstract concrete — "this is what each layer actually produces."

---

## A. Input

### A.1 The tender (excerpt)

> **NIT No. T-CRPF-2026-CONST-014** — Construction of two-storey administrative block at CRPF Group Centre, Pinjore.
>
> **Section 4 — Bid Eligibility Criteria.** The bidder shall have:
>
> 4.1 a minimum annual turnover of **Rs. 5 (five) crore** in any of the last three financial years;
>
> 4.2 successfully completed **at least three (3) similar projects** of value not less than Rs. 2 crore each in the **last five (5) years** as on the bid submission date;
>
> 4.3 a **valid GST registration**;
>
> 4.4 **ISO 9001 certification** (Quality Management System) issued by a body accredited under IAF MLA.

### A.2 The bidder pool

Ten bidders submit bundles. The mix:

| # | Bidder | Doc mix | Notes |
|---|---|---|---|
| 1 | ABC Constructions | All typed PDFs | Clean |
| 2 | XYZ Infra | Typed + 1 scanned | Clean |
| 3 | PQR Builders | Typed + scans | Shares director with #8 |
| 4 | LMN Engineers | All typed | Only 2 similar projects |
| 5 | RST Engineering | Typed + scan | ISO cert not in IAF registry |
| 6 | DEF Constructions | All typed | Clean |
| 7 | GHI Infra | Typed + 1 photographed certificate | Turnover scan is poor quality (the brief's amber case) |
| 8 | JKL Builders | Typed + scans | Shares director with #3 |
| 9 | UVW Constructions | All typed | Clean |
| 10 | OPQ Engineers | Typed + 1 docx | Clean |

---

## B. After the Cartographer (CriterionDSL)

```yaml
tender:
  id: T-CRPF-2026-CONST-014
  source_sha256: e3a1c4...
  classification: construction_services

criteria:
  - id: C1
    type: financial
    mandatory: true
    mandatory_confidence: 0.97
    text: "Minimum annual turnover of Rs. 5 crore in any of the last 3 FYs"
    constraint:
      field: annual_turnover_inr
      op: ">="
      value: 50000000
      window: { last_n_fy: 3, aggregator: any }
    evidence_required: [audited_financial_statement, ca_certificate]
    validators: [icai_udin_lookup]

  - id: C2
    type: technical
    mandatory: true
    mandatory_confidence: 0.96
    text: "At least 3 similar projects of >= Rs.2 cr each in last 5 years"
    constraint:
      field: completed_projects
      filter:
        similarity_to_tender_scope: ">= 0.75"
        value_inr: ">= 20000000"
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
    validators: [gstn_api_lookup]

  - id: C4
    type: certification
    mandatory: true
    mandatory_confidence: 0.94
    text: "ISO 9001 certification (IAF MLA accredited)"
    constraint:
      field: iso_9001
      op: "exists + valid_on(today) + accredited_by_iaf_mla"
    validators: [iso_accreditation_body_lookup]
```

The officer reviews this in the UI. The four cards are confirmed unchanged. The DSL is locked.

---

## C. After the Excavator (one bidder's Evidence Graph excerpt)

For Bidder 7 (the brief's amber case), here is a slice of the evidence graph:

```json
[
  {
    "field": "annual_turnover_inr",
    "value": 51200000,
    "fy": "2023-24",
    "source": {
      "doc_id": "bidder_07/audited_fs_2023_24.pdf",
      "doc_sha256": "9f2b...",
      "page": 14,
      "bbox": [121, 488, 312, 511],
      "ocr_conf": 0.62,
      "extractor_conf": 0.81,
      "provenance_match_conf": 0.95,
      "final_conf": 0.62
    }
  },
  {
    "field": "annual_turnover_inr",
    "value": 50200000,
    "fy": "2023-24",
    "source": {
      "doc_id": "bidder_07/ca_certificate.pdf",
      "doc_sha256": "5d31...",
      "page": 1,
      "bbox": [60, 220, 480, 252],
      "ocr_conf": 0.97,
      "extractor_conf": 0.92,
      "provenance_match_conf": 0.99,
      "final_conf": 0.92
    }
  },
  {
    "field": "gstin",
    "value": "06ABCDE1234F1Z5",
    "source": {
      "doc_id": "bidder_07/gst_rc.pdf",
      "doc_sha256": "1a78...",
      "page": 1,
      "bbox": [102, 312, 360, 332],
      "ocr_conf": 0.99,
      "extractor_conf": 0.99,
      "provenance_match_conf": 1.0,
      "final_conf": 0.99
    }
  },
  {
    "field": "completed_projects",
    "value": [
      { "name": "...Boys Hostel CRPF Bantalab",  "value_inr": 38000000, "completed_on": "2023-09-12", "similarity": 0.82 },
      { "name": "...Mess Block CRPF Pallipuram", "value_inr": 27500000, "completed_on": "2022-03-20", "similarity": 0.78 },
      { "name": "...Quarter Guard Avadi",        "value_inr": 22000000, "completed_on": "2024-01-08", "similarity": 0.81 },
      { "name": "...Storeroom Bldg PT Sch",      "value_inr": 21500000, "completed_on": "2021-11-30", "similarity": 0.76 }
    ],
    "source": "completion_certificate set + work_order set (4 documents)"
  },
  {
    "field": "iso_9001",
    "value": { "issuer": "TUV Rheinland", "cert_no": "TR/2023/0991", "issued": "2023-04-12", "valid_to": "2026-04-11" },
    "source": {
      "doc_id": "bidder_07/iso9001_cert.pdf",
      "doc_sha256": "7e30...",
      "page": 1,
      "bbox": [40, 200, 580, 480],
      "ocr_conf": 0.95,
      "extractor_conf": 0.97,
      "final_conf": 0.95
    }
  }
]
```

Cross-document agreement on `annual_turnover_inr` for FY 2023-24: two values within 2% (51.2 vs 50.2 lakh). The disagreement is small but the lower-confidence node (`final_conf = 0.62`) is the one with the higher value. We will see in the next section how the Adjudicator handles this.

---

## D. After the Adjudicator (verdicts for Bidder 7)

```json
[
  {
    "criterion_id": "C1",
    "status": "manual_review",
    "confidence": 0.62,
    "reason_tag": "evidence_low_confidence",
    "reason_text": "Turnover figure on page 14 of audited_fs_2023_24.pdf has OCR confidence 0.62; please verify.",
    "evidence_used": ["e_117 (FS, conf 0.62)", "e_118 (CA cert, conf 0.92)"],
    "skeptic": { "outcome": "counter", "counter": "FS-derived value 5.12 cr disagrees with CA-derived 5.02 cr by 2%; FS conf is low" },
    "validators": { "icai_udin_lookup": "verified" },
    "suggested_action": "Re-upload a higher-DPI scan of pages 12-16 of the audited financial statement, or provide ITR for FY 2023-24."
  },
  {
    "criterion_id": "C2",
    "status": "eligible",
    "confidence": 0.91,
    "reason_text": "4 of 4 listed projects meet the 'similar + >= Rs.2 cr + completed in last 5 years' filter; threshold of 3 met."
  },
  {
    "criterion_id": "C3",
    "status": "eligible",
    "confidence": 0.99,
    "reason_text": "GSTIN 06ABCDE1234F1Z5 confirmed active by GSTN API."
  },
  {
    "criterion_id": "C4",
    "status": "eligible",
    "confidence": 0.95,
    "reason_text": "ISO 9001 cert TR/2023/0991 valid through 2026-04-11; issuer TUV Rheinland accredited under IAF MLA."
  }
]
```

Overall verdict for Bidder 7: **Manual Review** (because C1 is Manual Review).

---

## E. After officer action

The officer clicks the amber C1 cell. The right pane shows the scanned page 14 with the bbox highlighted on the value `Rs. 5,12,00,000`. The officer can see why OCR struggled — the print is faded.

Officer requests a clearer scan from the bidder. Uploads it. Clicks **Re-evaluate C1**. The system re-runs the Excavator on just that document, gets `final_conf = 0.94`, the Adjudicator returns `eligible`, the cell turns green.

Bidder 7's overall verdict becomes **Eligible**.

---

## F. After the Integrity Layer

```json
[
  {
    "category": "cartel",
    "severity": "warning",
    "claim": "Bidder 3 (PQR Builders) and Bidder 8 (JKL Builders) share director Rajesh Kumar (DIN 00123456); their bid prices differ by 1.2%.",
    "evidence": [
      "MCA21 lookup of bidder_03 CIN -> directors include DIN 00123456",
      "MCA21 lookup of bidder_08 CIN -> directors include DIN 00123456",
      "bid_price(b3) = Rs.4,82,15,000 ; bid_price(b8) = Rs.4,87,98,000 ; delta = 1.21%"
    ],
    "suggested_action": "Refer to vigilance for review; request explanation per CVC guidelines."
  },
  {
    "category": "forgery",
    "severity": "critical",
    "claim": "Bidder 5's ISO 9001 certificate ICW/2023/9876 is not present in the IAF MLA accreditation registry of issuer 'Intl. Cert. World'.",
    "evidence": [
      "ISO accreditation body lookup returned 'not found' for cert ICW/2023/9876",
      "Issuer 'Intl. Cert. World' is not a recognized IAF MLA member as of 2026-04-22"
    ],
    "suggested_action": "Mark Bidder 5 for review; consider Not Eligible against C4 if unverified."
  }
]
```

Bidder 5's overall verdict is downgraded to **Manual Review** because of the Critical Integrity finding.

---

## G. The final report

| # | Bidder | C1 | C2 | C3 | C4 | Overall | Notes |
|---|---|---|---|---|---|---|---|
| 1 | ABC Constructions | ✓ | ✓ | ✓ | ✓ | **Eligible** | |
| 2 | XYZ Infra | ✓ | ✓ | ✓ | ✓ | **Eligible** | |
| 3 | PQR Builders | ✓ | ✓ | ✓ | ✓ | **Eligible** | Integrity: shared director with #8 |
| 4 | LMN Engineers | ✓ | ✗ (only 2) | ✓ | ✓ | **Not Eligible** | |
| 5 | RST Engineering | ✓ | ✓ | ✓ | ⚠ | **Manual Review** | ISO not in registry |
| 6 | DEF Constructions | ✓ | ✓ | ✓ | ✓ | **Eligible** | |
| 7 | GHI Infra | ✓ (after rescan) | ✓ | ✓ | ✓ | **Eligible** | Was Manual Review pre-rescan |
| 8 | JKL Builders | ✓ | ✓ | ✓ | ✓ | **Eligible** | Integrity: shared director with #3 |
| 9 | UVW Constructions | ✓ | ✓ | ✓ | ✓ | **Eligible** | |
| 10 | OPQ Engineers | ✓ | ✓ | ✓ | ✓ | **Eligible** | |

Officer signs. The bundle includes:

- The four-criterion DSL
- Each bidder's full Evidence Graph
- All 40 verdicts (10 bidders × 4 criteria) + 10 overall verdicts
- Two Integrity findings
- One officer override (the rescan re-evaluation for Bidder 7 — recorded as `evidence_refresh` rather than override)
- All pinned model and policy versions
- Hash-chained ledger root + ECDSA signature

The `.pramaan` archive is downloaded. `pramaan ledger verify` returns `OK`. `pramaan replay --bundle ...` produces a byte-identical bundle.

This is the system the brief asks for. This is what we will demo.

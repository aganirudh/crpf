# Procurement Officer UX

The single most important user is the procurement officer who has to sign the report. If they cannot trust what they see, the system has failed regardless of how good the AI is. This document specifies the officer-facing application.

---

## 1. Design tenets

1. **A procurement file, not a notebook.** The UI must read like a familiar government file (left-to-right, top-to-bottom, with stamps and references), not like an ML dashboard.
2. **One click from cell to source pixel.** Every value in the report is a hyperlink to the exact bbox in the source PDF.
3. **Manual Review is a workflow, not an error.** Amber cases come with a *suggested action* and a one-click path to that action.
4. **Overrides are heavyweight on purpose.** Overriding a verdict requires entering a reason and a tag from a controlled vocabulary. Friction is feature, not bug.
5. **Sign-off is a deliberate act.** The officer signs a report, not a session.

---

## 2. The five screens

### 2.1 Tender intake

Officer uploads the tender PDF. The system runs the Cartographer in the background and notifies the officer when the CriterionDSL is ready.

```
┌─────────────────────────────────────────────────────────────────────┐
│ PRAMAAN  /  New Evaluation                                          │
├─────────────────────────────────────────────────────────────────────┤
│ Tender file:    [ tender_construction_2026.pdf ]   [Browse]         │
│ Reference no:   T-CRPF-2026-CONST-014                                │
│ Department:     Construction Wing, CRPF                              │
│                                                                       │
│ [ Begin extraction ]                                                  │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 CriterionDSL review

The Cartographer's output rendered as cards. Officer can edit, toggle mandatory, add, delete. The "Source" link on each card opens the tender PDF at the bbox that justified the criterion.

```
┌──── Criterion C1 · Financial ──── Mandatory [✓] ─────────────────────┐
│ Minimum annual turnover of Rs. 5 crore in any of the last 3 FYs      │
│ ─────────────────────────────────────────────────────────────────────│
│ Field:        annual_turnover_inr                                    │
│ Threshold:    ≥ Rs. 5,00,00,000                                      │
│ Window:       last 3 FYs (any)                                       │
│ Evidence:     Audited FS, CA Certificate                             │
│ Validators:   ICAI UDIN lookup                                       │
│ ─────────────────────────────────────────────────────────────────────│
│ [ Edit ]   [ Source: page 23, lines 410-462 ]   [ Delete ]           │
└──────────────────────────────────────────────────────────────────────┘
```

When all cards are confirmed, officer clicks **Lock criteria** and proceeds.

### 2.3 Bidder intake

Officer uploads bidder bundles. Each bundle can be a folder or a zip. The system runs the Excavator on each in parallel.

```
┌─────────────────────────────────────────────────────────────────────┐
│ Bidders for T-CRPF-2026-CONST-014                                    │
├──────────────────────────────────────────────────────────────────────┤
│ Bidder 01  ABC Constructions      [ ✓ Processed · 14 docs · 2:18 ]   │
│ Bidder 02  XYZ Infra              [ ⟳ Processing · 8/22 docs ]       │
│ Bidder 03  PQR Builders           [ ⚠ Photo of ISO cert needs review]│
│ ...                                                                   │
│ [ + Add bidder ]                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.4 The report (the main screen)

Two-pane split. Left: the report grid. Right: the source PDF viewer.

```
┌─────────────────────── REPORT ────────────────────────┬──── SOURCE ─────────────┐
│         │   C1     │   C2     │   C3     │   C4   ││ audited_fs_2023_24.pdf  │
│         │ turnover │ projects │   GST    │  ISO   ││ Page 14 of 42           │
├─────────┼──────────┼──────────┼──────────┼────────┤│ ┌─────────────────────┐ │
│ Bidder1 │ ✓ 7.2 cr │ ✓ 4 ✓    │ ✓ active │ ✓ valid││ │ ...                 │ │
│ Bidder2 │ ✓ 9.1 cr │ ✓ 3 ✓    │ ✓ active │ ✓ valid││ │ ┌─────────────────┐ │ │
│ Bidder3 │ ✗ 3.8 cr │ ✓ 5 ✓    │ ✓ active │ ✓ valid││ │ │ Turnover:       │ │ │
│ Bidder4 │ ✓ 6.4 cr │ ✗ 2 only │ ✓ active │ ✓ valid││ │ │ Rs. 5,12,00,000 │ │ │
│ Bidder5 │ ✓ 5.5 cr │ ✓ 3 ✓    │ ✓ active │ ✗ exp  ││ │ └─────────────────┘ │ │
│ Bidder6 │ ✓ 8.0 cr │ ✓ 7 ✓    │ ✓ active │ ✓ valid││ │ ...                 │ │
│ Bidder7 │ ⚠ 5.12cr*│ ✓ 4 ✓    │ ✓ active │ ✓ valid││ └─────────────────────┘ │
│ Bidder8 │ ✓ 6.0 cr │ ✓ 3 ✓    │ ✗ susp.  │ ✓ valid││                          │
│ Bidder9 │ ✓ 7.5 cr │ ✓ 6 ✓    │ ✓ active │ ✓ valid││ OCR confidence: 0.62     │
│ Bidder10│ ✓ 5.8 cr │ ✓ 3 ✓    │ ✓ active │ ✓ valid││ Cross-doc: ✓ within 2%   │
│         │          │          │          │        ││                          │
│ Overall │ ✓ Eligible : 6  ✗ Not Eligible : 3  ⚠ Manual Review : 1            │
└─────────┴──────────┴──────────┴──────────┴────────┴──────────────────────────┘
                                       ↑
                          Currently selected: Bidder7 / C1
```

Behavior:

- Cell colors: green (Eligible), red (Not Eligible), amber (Manual Review).
- Click any cell → right pane jumps to the source document, page, and bbox.
- Tooltip on each cell: extracted value, confidence, reason.
- The amber cell shows a small `*` indicating Manual Review with hover for the reason.

### 2.5 The Verdict drawer

Selecting a cell opens a side-drawer with the full verdict object — readable, not raw JSON.

```
┌─ Verdict · Bidder7 · C1 (Turnover) ──────────────────────────── ⚠ Manual Review ─┐
│                                                                                    │
│ Reason: Turnover figure on page 14 of audited_fs_2023_24.pdf has OCR confidence    │
│         0.62; please verify.                                                       │
│                                                                                    │
│ Suggested action: Re-upload a higher-DPI scan of pages 12-16 of the audited       │
│         financial statement, or provide the ITR for FY 2023-24 to cross-validate.  │
│                                                                                    │
│ Evidence used:                                                                     │
│   • audited_fs_2023_24.pdf · p.14 · Rs. 5,12,00,000  · conf 0.62  [view]          │
│   • ca_certificate.pdf · p.1  · Rs. 5,02,00,000  · conf 0.93        [view]        │
│                                                                                    │
│ Skeptic: agreed within 2% tolerance, but flagged FS confidence as low.            │
│ Validator (ICAI UDIN): ✓ verified · UDIN 23123456BLPGAA1234                       │
│                                                                                    │
│ [ Re-upload evidence ]   [ Override verdict... ]   [ Mark resolved ]              │
└────────────────────────────────────────────────────────────────────────────────────┘
```

### 2.6 Override dialog

Heavy by design. The officer must:

```
┌─ Override Verdict · Bidder7 · C1 ─────────────────────────────────────┐
│                                                                        │
│ Original verdict:  ⚠ Manual Review                                     │
│ New verdict:       [ Eligible ▼ ]                                      │
│                                                                        │
│ Reason tag:        [ Verified telephonically with bidder ▼ ]           │
│                    (controlled vocabulary)                             │
│                                                                        │
│ Reason text:       ┌──────────────────────────────────────────────┐    │
│                    │ Bidder confirmed turnover; supplementary ITR │    │
│                    │ uploaded to file 7-supp.pdf and matches.    │    │
│                    └──────────────────────────────────────────────┘    │
│                                                                        │
│ Officer:           Inspector A. B. Singh (officer:abc@crpf.gov.in)     │
│                                                                        │
│ ⚠ This override will be permanently recorded in the audit ledger.     │
│                                                                        │
│              [ Cancel ]                  [ Confirm override ]          │
└────────────────────────────────────────────────────────────────────────┘
```

Reason tag vocabulary (extensible per organization):

- `verified_telephonically_with_bidder`
- `supplementary_evidence_provided_offline`
- `clarification_received_in_pre_bid`
- `data_entry_error_in_extraction`
- `ocr_misread_corrected_manually`
- `validator_unavailable_verified_offline`
- `committee_decision`
- `other_with_explanation`

### 2.7 The Integrity Panel

A separate tab showing cross-bidder findings (see `08-integrity-layer.md`):

```
┌─ Integrity Findings ───────────────────────────────────────────────────┐
│                                                                         │
│  ⚠ Common director across bidders                                       │
│     Bidder3 (PQR Builders) and Bidder8 (RST Engineering) share          │
│     director Rajesh Kumar (DIN 00123456). Both bid prices within 2%.    │
│     [ View linkage graph ]                                              │
│                                                                         │
│  ⚠ ISO certificate not in accreditation registry                        │
│     Bidder5: ISO 9001 cert no. ICW/2023/9876 not found in IAF body      │
│     registry of issuer "Intl. Cert. World".                             │
│     [ View certificate ]   [ Try alternate spellings ]                  │
│                                                                         │
│  ℹ Capacity ratio                                                       │
│     Bidder4 lists 3 concurrent projects of >Rs.50cr each but EPFO       │
│     contribution shows only 8 employees in 2023-24.                     │
│     [ View employee filings ]                                           │
└─────────────────────────────────────────────────────────────────────────┘
```

These are *informational*; they do not change verdicts. Officer judgment.

### 2.8 Sign-off

When the officer is ready, they click **Sign and Export**. They are shown a final summary, asked to enter their PIN (HSM-backed), and the bundle is signed and downloaded.

```
┌─ Sign Evaluation Report ───────────────────────────────────────────────┐
│                                                                         │
│ Tender:       T-CRPF-2026-CONST-014                                    │
│ Bidders:      10                                                        │
│ Eligible:     7   (after 1 override)                                    │
│ Not Eligible: 3                                                         │
│ Manual Review: 0  (all resolved)                                        │
│ Overrides:    1                                                         │
│ Integrity flags: 3 reviewed                                             │
│                                                                         │
│ This will produce a signed report bundle and append a `report.signed`   │
│ event to the audit ledger. The bundle will be exported as PDF and       │
│ .pramaan archive.                                                       │
│                                                                         │
│ Enter signing PIN: [ ******** ]                                         │
│                                                                         │
│              [ Cancel ]                  [ Sign and Export ]            │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Accessibility and accessibility

- Keyboard-navigable end-to-end.
- WCAG 2.2 AA color contrasts; cells distinguished by icon + color, not color alone.
- Hindi locale support; criterion text shown in original tender language with translation toggle.
- Print-friendly stylesheet for the PDF export.

---

## 4. Stack

- Next.js 15 (App Router) + TypeScript.
- shadcn/ui for the component library (accessible, themable, no proprietary lock-in).
- `react-pdf` for the right-pane viewer with a custom bbox-overlay layer.
- TanStack Table for the report grid.
- Server Components for the report initial render; Client Components for the interactive panes.
- All officer actions go through the FastAPI gateway with OIDC; no client-side trust.

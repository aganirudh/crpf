"""Deterministic LLM mock for offline / CI / no-API-key development.

Returns plausible-shaped responses for any pydantic model the system asks
for. Used by `LLMClient` when `settings.is_mock_llm` is True.

Notes:
  * The mock for `CriterionDSL` returns the brief's exact 4-criterion sample
    so the demo flow keeps working without an API key.
  * The mock for `DocumentExtraction` (W3 field extractor) inspects the
    user prompt text for likely values and quotes them verbatim, so the
    Excavator's `source_quote → bbox` realignment step still succeeds.
  * For arbitrary pydantic models we fill in zero-values via Pydantic's
    `model_construct`.
"""

from __future__ import annotations

import re
from typing import Any, TypeVar, get_args, get_origin

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def fake_extract[T: BaseModel](model: type[T], *, system: str, user: str) -> T:
    """Return a deterministic stub instance of `model`.

    Specialises for the well-known schema we care about; otherwise produces
    a typed zero-value via `model_construct`.
    """
    name = model.__name__

    if name == "CriterionDSL":
        return _sample_criterion_dsl(model)  # type: ignore[return-value]

    if name == "DocumentExtraction":
        return _sample_document_extraction(model, user_prompt=user)  # type: ignore[return-value]

    return _zero_construct(model)


def fake_chat(*, system: str, user: str) -> str:
    """A bland, deterministic response for the Skeptic / chat use-cases."""
    if "skeptic" in system.lower() or "counter" in system.lower():
        return "accept: no non-trivial counter-argument identified in the available evidence."
    return "(mock LLM response)"


# ─── Internals ────────────────────────────────────────────────────────────


def _sample_criterion_dsl(model: type[BaseModel]) -> BaseModel:
    """The brief's 4-criterion construction-tender sample DSL."""
    sample: dict[str, Any] = {
        "dsl_version": "v1",
        "tender": {
            "id": "T-CRPF-2026-CONST-014",
            "source_sha256": "0" * 64,
            "classification": "construction_services",
            "language": "en",
            "pages": 142,
        },
        "criteria": [
            {
                "id": "C1",
                "type": "financial",
                "mandatory": True,
                "mandatory_confidence": 0.97,
                "text": "Minimum annual turnover of Rs. 5 crore in any of the last 3 FYs",
                "constraint": {
                    "kind": "scalar",
                    "field": "annual_turnover_inr",
                    "op": ">=",
                    "value": 50_000_000,
                    "window": {"last_n_fy": 3, "aggregator": "any"},
                },
                "evidence_required": ["audited_financial_statement", "ca_certificate"],
                "validators": ["icai_udin_lookup"],
                "cross_check": [{"against": "itr", "tolerance_pct": 5}],
            },
            {
                "id": "C2",
                "type": "technical",
                "mandatory": True,
                "mandatory_confidence": 0.96,
                "text": "At least 3 similar projects of >= Rs.2 cr each in last 5 years",
                "constraint": {
                    "kind": "set",
                    "field": "completed_projects",
                    "filter": {
                        "similarity_to_tender_scope": ">= 0.75",
                        "value_inr": ">= 20000000",
                        "status": "completed",
                        "completion_date": ">= today - 5y",
                    },
                    "op": "count >=",
                    "value": 3,
                },
                "evidence_required": ["completion_certificate", "work_order"],
            },
            {
                "id": "C3",
                "type": "compliance",
                "mandatory": True,
                "mandatory_confidence": 0.99,
                "text": "Valid GST registration",
                "constraint": {
                    "kind": "scalar",
                    "field": "gstin",
                    "op": "regex_match + active_on(today)",
                    "value": r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]{3}$",
                },
                "evidence_required": ["gst_registration_certificate"],
                "validators": ["gstn_api_lookup"],
            },
            {
                "id": "C4",
                "type": "certification",
                "mandatory": True,
                "mandatory_confidence": 0.94,
                "text": "ISO 9001 certification (IAF MLA accredited)",
                "constraint": {
                    "kind": "scalar",
                    "field": "iso_9001",
                    "op": "exists + valid_on(today) + accredited_by_iaf_mla",
                },
                "evidence_required": ["iso_certificate"],
                "validators": ["iso_accreditation_body_lookup"],
            },
        ],
        "evidence_vocabulary": {
            "audited_financial_statement": {
                "aliases": ["audited financials", "balance sheet", "P&L statement"],
                "expected_fields": ["annual_turnover_inr", "fy", "auditor_name"],
            },
            "ca_certificate": {
                "aliases": ["CA certificate", "turnover certificate"],
                "expected_fields": ["annual_turnover_inr", "fy", "ca_name", "udin"],
            },
            "gst_registration_certificate": {
                "aliases": ["GST RC", "GSTIN certificate", "Form GST REG-06"],
                "expected_fields": ["gstin", "legal_name", "registration_date"],
            },
            "iso_certificate": {
                "aliases": ["ISO 9001 certificate", "QMS certificate"],
                "expected_fields": ["issuer", "cert_no", "issued", "valid_to"],
            },
        },
    }
    return model.model_validate(sample)


# ─── DocumentExtraction mock ──────────────────────────────────────────────


_FILENAME_RE = re.compile(r"^Document filename:\s*(.+)$", re.MULTILINE)
_PAGE_MARKER = re.compile(r"\[PAGE\s+(\d+)\]")


def _sample_document_extraction(model: type[BaseModel], *, user_prompt: str) -> BaseModel:
    """Inspect the prompt body and emit plausible `DocumentExtraction`.

    The mock searches the document text for likely values, ensures the
    `source_quote` is a verbatim substring, and sets a realistic page
    number using the `[PAGE N]` markers the Excavator inserts.
    """
    fname_match = _FILENAME_RE.search(user_prompt)
    filename = (fname_match.group(1) if fname_match else "").lower()

    body_start = user_prompt.find("--- DOCUMENT TEXT BEGINS ---")
    body_end = user_prompt.find("--- DOCUMENT TEXT ENDS ---")
    body = (
        user_prompt[body_start + len("--- DOCUMENT TEXT BEGINS ---") : body_end]
        if body_start != -1 and body_end != -1
        else user_prompt
    )

    pages = _split_by_page(body)

    # Filename → likely document_kind + which extractors to run.
    kind, builders = _route_filename(filename)

    fields: list[dict] = []
    for builder in builders:
        fields.extend(builder(pages))

    return model.model_validate({
        "document_kind": kind,
        "fields": fields,
        "notes": None,
    })


def _split_by_page(body: str) -> list[tuple[int, str]]:
    """Returns [(page_no, text)] in order. If no markers, treat as page 1."""
    parts: list[tuple[int, str]] = []
    if "[PAGE" not in body:
        return [(1, body)]
    indices = [(m.start(), int(m.group(1))) for m in _PAGE_MARKER.finditer(body)]
    for idx, (start, page_no) in enumerate(indices):
        end = indices[idx + 1][0] if idx + 1 < len(indices) else len(body)
        # Skip past the marker itself.
        marker_end = body.find("\n", start)
        text = body[marker_end + 1 if marker_end != -1 else start : end]
        parts.append((page_no, text))
    return parts


def _route_filename(name: str) -> tuple[str, list]:
    """Map filename hints to (document_kind, list of field builders)."""
    if any(t in name for t in ("audit", "audited_fs", "balance", "p_l", "pl_")):
        return ("audited_financial_statement", [_extract_turnover, _extract_legal_name])
    if "ca_cert" in name or "ca-cert" in name or "turnover_cert" in name or "ca_certificate" in name:
        return ("ca_certificate", [_extract_turnover, _extract_udin, _extract_legal_name])
    if "gst" in name or "reg-06" in name or "reg_06" in name:
        return ("gst_registration_certificate", [_extract_gstin, _extract_legal_name])
    if "iso" in name and ("9001" in name or "qms" in name or "iso" in name):
        return ("iso_certificate", [_extract_iso])
    if "epf" in name or "pf_" in name or "pf-" in name:
        return ("epf_registration", [_extract_epf])
    if "esi" in name:
        return ("esi_registration", [_extract_esi])
    if "pan" in name:
        return ("pan_card", [_extract_pan])
    if "cin" in name or "moa" in name or "incorp" in name:
        return ("cin_proof", [_extract_cin, _extract_legal_name])
    if "completion" in name:
        return ("completion_certificate", [_extract_completion])
    if "work_order" in name or "work-order" in name or "workorder" in name:
        return ("work_order", [_extract_completion])
    if "blacklist" in name or "non_blacklist" in name:
        return ("blacklist_declaration", [_extract_blacklist])

    # Default — attempt every extractor; keep only the matches that ground.
    return (
        "unknown",
        [
            _extract_turnover, _extract_gstin, _extract_pan, _extract_cin,
            _extract_iso, _extract_legal_name,
        ],
    )


# ─── Field-specific scanners ──────────────────────────────────────────────


_RS_NUMBER_RE = re.compile(
    r"(?:Rs\.?|INR|₹|Rupees)\s*([\d,]+(?:\.\d+)?)\s*(crore|cr\.?|lakh|lakhs|lac|lacs)?",
    re.IGNORECASE,
)
_FY_INLINE_RE = re.compile(
    r"\bFY\s*\d{2,4}\s*[-/]\s*\d{2,4}\b|\bAY\s*\d{4}\s*[-/]\s*\d{2,4}\b|\b20\d{2}\s*[-/]\s*\d{2,4}\b"
)
_GSTIN_RE = re.compile(r"\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]{3}\b")
_PAN_RE = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")
_CIN_RE = re.compile(r"\b[LU][0-9]{5}[A-Z]{2}[0-9]{4}[A-Z]{3}[0-9]{6}\b")
_UDIN_RE = re.compile(r"\b\d{2}[A-Z0-9]{6,8}\d{6,12}\b")
_DATE_RE = re.compile(
    r"\b\d{1,2}\s*[-/\.]\s*\d{1,2}\s*[-/\.]\s*\d{2,4}\b|"
    r"\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4}\b"
)


def _extract_turnover(pages: list[tuple[int, str]]) -> list[dict]:
    out: list[dict] = []
    for page_no, text in pages:
        for m in _RS_NUMBER_RE.finditer(text):
            quote_start = max(0, m.start() - 30)
            quote_end = min(len(text), m.end() + 60)
            quote = text[quote_start:quote_end].strip()
            # Try to find a nearby FY in the same window.
            window = text[max(0, m.start() - 80) : min(len(text), m.end() + 80)]
            fy_match = _FY_INLINE_RE.search(window)
            from pramaan.dsl.normalize import parse_fy
            fy = parse_fy(fy_match.group(0)) if fy_match else None

            value_str = m.group(0)
            out.append({
                "field": "annual_turnover_inr",
                "value": value_str.strip(),
                "fy": fy,
                "page": page_no,
                "source_quote": quote[:120],
                "extractor_confidence": 0.92,
            })
            if len(out) >= 6:
                return out
    return out


def _extract_gstin(pages: list[tuple[int, str]]) -> list[dict]:
    out: list[dict] = []
    for page_no, text in pages:
        for m in _GSTIN_RE.finditer(text):
            quote = text[max(0, m.start() - 20) : min(len(text), m.end() + 20)].strip()
            out.append({
                "field": "gstin",
                "value": m.group(0),
                "page": page_no,
                "source_quote": quote[:120],
                "extractor_confidence": 0.97,
            })
            if len(out) >= 1:
                return out
    return out


def _extract_pan(pages: list[tuple[int, str]]) -> list[dict]:
    out: list[dict] = []
    for page_no, text in pages:
        for m in _PAN_RE.finditer(text):
            quote = text[max(0, m.start() - 15) : min(len(text), m.end() + 15)].strip()
            out.append({
                "field": "pan",
                "value": m.group(0),
                "page": page_no,
                "source_quote": quote[:120],
                "extractor_confidence": 0.96,
            })
            return out
    return out


def _extract_cin(pages: list[tuple[int, str]]) -> list[dict]:
    out: list[dict] = []
    for page_no, text in pages:
        for m in _CIN_RE.finditer(text):
            quote = text[max(0, m.start() - 15) : min(len(text), m.end() + 15)].strip()
            out.append({
                "field": "cin",
                "value": m.group(0),
                "page": page_no,
                "source_quote": quote[:120],
                "extractor_confidence": 0.95,
            })
            return out
    return out


def _extract_udin(pages: list[tuple[int, str]]) -> list[dict]:
    out: list[dict] = []
    for page_no, text in pages:
        for m in _UDIN_RE.finditer(text):
            if "UDIN" not in text[max(0, m.start() - 30) : m.start() + 5].upper():
                continue
            quote = text[max(0, m.start() - 30) : min(len(text), m.end() + 10)].strip()
            out.append({
                "field": "udin",
                "value": m.group(0),
                "page": page_no,
                "source_quote": quote[:120],
                "extractor_confidence": 0.9,
            })
            return out
    return out


def _extract_iso(pages: list[tuple[int, str]]) -> list[dict]:
    out: list[dict] = []
    for page_no, text in pages:
        cert_no = re.search(r"(?:Certificate\s*(?:No\.?|Number)\s*[:\-]?\s*)([A-Z0-9\-/]+)", text, re.IGNORECASE)
        if cert_no:
            quote = text[max(0, cert_no.start()) : min(len(text), cert_no.end() + 10)].strip()
            out.append({
                "field": "iso_certificate_no",
                "value": cert_no.group(1),
                "page": page_no,
                "source_quote": quote[:120],
                "extractor_confidence": 0.9,
            })
        std = re.search(r"\bISO\s+9001(?::\d{4})?\b", text)
        if std:
            quote = text[max(0, std.start() - 5) : min(len(text), std.end() + 30)].strip()
            out.append({
                "field": "iso_standard",
                "value": std.group(0),
                "page": page_no,
                "source_quote": quote[:120],
                "extractor_confidence": 0.97,
            })
        valid = re.search(r"(?:Valid\s+(?:until|to|till)|Validity)[:\s]+(\d{1,2}\s*[-/\.]\s*\d{1,2}\s*[-/\.]\s*\d{2,4})", text, re.IGNORECASE)
        if valid:
            quote = text[max(0, valid.start()) : min(len(text), valid.end())].strip()
            out.append({
                "field": "iso_valid_to",
                "value": valid.group(1),
                "page": page_no,
                "source_quote": quote[:120],
                "extractor_confidence": 0.85,
            })
        issuer = re.search(r"(?:Issued\s+by|Issuing\s+Body|Certifying\s+Body)\s*[:\-]?\s*([^\n]{3,80})", text, re.IGNORECASE)
        if issuer:
            quote = text[max(0, issuer.start()) : min(len(text), issuer.end())].strip()
            out.append({
                "field": "iso_issuer",
                "value": issuer.group(1).strip(),
                "page": page_no,
                "source_quote": quote[:120],
                "extractor_confidence": 0.85,
            })
        if out:
            return out
    return out


def _extract_legal_name(pages: list[tuple[int, str]]) -> list[dict]:
    pattern = re.compile(
        r"\b([A-Z][A-Za-z&'\.\- ]{2,60}?\s+(?:Pvt\.?\s*Ltd\.?|Private\s+Limited|Limited|LLP))\b"
    )
    for page_no, text in pages:
        m = pattern.search(text)
        if m:
            quote = text[max(0, m.start()) : min(len(text), m.end())].strip()
            return [{
                "field": "legal_name",
                "value": m.group(1).strip(),
                "page": page_no,
                "source_quote": quote[:120],
                "extractor_confidence": 0.85,
            }]
    return []


def _extract_epf(pages: list[tuple[int, str]]) -> list[dict]:
    for page_no, text in pages:
        m = re.search(r"(?:EPF|PF)\s*(?:Reg(?:istration)?\.?\s*No\.?|Code)\s*[:\-]?\s*([A-Z0-9/\-]+)", text, re.IGNORECASE)
        if m:
            quote = text[max(0, m.start()) : min(len(text), m.end())].strip()
            return [{
                "field": "epf_registration_no",
                "value": m.group(1),
                "page": page_no,
                "source_quote": quote[:120],
                "extractor_confidence": 0.9,
            }]
    return []


def _extract_esi(pages: list[tuple[int, str]]) -> list[dict]:
    for page_no, text in pages:
        m = re.search(r"\bESI[CN]?\s*(?:Reg(?:istration)?\.?\s*No\.?|Code|Number)\s*[:\-]?\s*([A-Z0-9/\-]+)", text, re.IGNORECASE)
        if m:
            quote = text[max(0, m.start()) : min(len(text), m.end())].strip()
            return [{
                "field": "esi_registration_no",
                "value": m.group(1),
                "page": page_no,
                "source_quote": quote[:120],
                "extractor_confidence": 0.9,
            }]
    return []


def _extract_completion(pages: list[tuple[int, str]]) -> list[dict]:
    out: list[dict] = []
    for page_no, text in pages:
        # Project value
        v = _RS_NUMBER_RE.search(text)
        if v:
            quote = text[max(0, v.start() - 30) : min(len(text), v.end() + 30)].strip()
            out.append({
                "field": "completed_project_value_inr",
                "value": v.group(0).strip(),
                "page": page_no,
                "source_quote": quote[:120],
                "extractor_confidence": 0.88,
            })
        # Project name (best effort: line beginning with "Project:" or quoted name)
        pname = re.search(r"(?:Project|Work)\s*(?:Name|Title)?\s*[:\-]\s*([^\n]{4,100})", text, re.IGNORECASE)
        if pname:
            quote = text[max(0, pname.start()) : min(len(text), pname.end())].strip()
            out.append({
                "field": "completed_project_name",
                "value": pname.group(1).strip(),
                "page": page_no,
                "source_quote": quote[:120],
                "extractor_confidence": 0.8,
            })
        owner = re.search(r"(?:Client|Owner|Issued\s+to)\s*[:\-]\s*([^\n]{3,100})", text, re.IGNORECASE)
        if owner:
            quote = text[max(0, owner.start()) : min(len(text), owner.end())].strip()
            out.append({
                "field": "completed_project_owner",
                "value": owner.group(1).strip(),
                "page": page_no,
                "source_quote": quote[:120],
                "extractor_confidence": 0.78,
            })
        compdate = re.search(
            r"(?:Completed|Completion(?:\s+Date)?|Date\s+of\s+Completion)\s*[:\-]\s*("
            r"\d{1,2}\s*[-/\.]\s*\d{1,2}\s*[-/\.]\s*\d{2,4}|"
            r"\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})",
            text, re.IGNORECASE,
        )
        if compdate:
            quote = text[max(0, compdate.start()) : min(len(text), compdate.end())].strip()
            out.append({
                "field": "completion_date",
                "value": compdate.group(1),
                "page": page_no,
                "source_quote": quote[:120],
                "extractor_confidence": 0.82,
            })
        if out:
            return out
    return out


def _extract_blacklist(pages: list[tuple[int, str]]) -> list[dict]:
    for page_no, text in pages:
        if re.search(r"not\s+(?:been\s+)?blacklisted", text, re.IGNORECASE):
            m = re.search(r"[^\n]{0,40}blacklist[^\n]{0,40}", text, re.IGNORECASE)
            quote = (m.group(0) if m else "blacklist").strip()
            return [{
                "field": "blacklist_declaration_present",
                "value": True,
                "page": page_no,
                "source_quote": quote[:120],
                "extractor_confidence": 0.95,
            }]
    return []


# ─── Internals ────────────────────────────────────────────────────────────


def _zero_construct(model: type[BaseModel]) -> BaseModel:
    """Build an instance using each field's default or a typed zero-value."""
    data: dict[str, Any] = {}
    for name, field in model.model_fields.items():
        if field.default is not None and field.default is not ...:
            continue  # Pydantic will fill from default
        if field.default_factory is not None:
            continue
        data[name] = _zero_for(field.annotation)
    try:
        return model.model_validate(data)
    except Exception:
        return model.model_construct(**data)


def _zero_for(tp: Any) -> Any:
    if tp is None or tp is type(None):
        return None
    origin = get_origin(tp)
    if origin in (list, tuple, set, frozenset):
        return []
    if origin is dict:
        return {}
    if isinstance(tp, type):
        if issubclass(tp, BaseModel):
            return _zero_construct(tp).model_dump()
        if issubclass(tp, str):
            return ""
        if issubclass(tp, bool):
            return False
        if issubclass(tp, (int, float)):
            return 0
    args = get_args(tp)
    if args:
        return _zero_for(args[0])
    return None

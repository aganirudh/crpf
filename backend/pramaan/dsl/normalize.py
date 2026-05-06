"""Value normalisers — bidders write the same datum in many ways.

The Excavator persists the normalised forms so the symbolic Adjudicator
can compare apples to apples. Each helper is small, pure, and tested.

Spec: `docs/04-document-pipeline.md` § 9 (Normalization).

Capabilities:
  * Indian-numbering parser ("Rs. 5 Crore", "₹5,00,00,000", "5.0 Cr") → INR rupees (int)
  * FY parser ("FY 23-24", "FY 2023-24", "AY 2024-25") → canonical "YYYY-YY" string
  * Date parser → ISO-8601 date string
  * GSTIN / PAN / CIN / UDIN regex validators

We deliberately keep regex-first: an LLM may *propose* a value but a
deterministic pure function decides whether it counts.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime

# ─── Money / Indian numbering ─────────────────────────────────────────────


_NUMBER_WITH_COMMAS = re.compile(r"[\d,]+(?:\.\d+)?")
_DECIMAL = re.compile(r"\d+(?:\.\d+)?")
_WORD_NUM = re.compile(r"[a-zA-Z]+")

_WORD_TO_NUM = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "fifteen": 15,
    "twenty": 20, "fifty": 50, "hundred": 100,
}


_UNIT_MULTIPLIERS_INR: dict[str, int] = {
    # canonical → multiplier in plain INR rupees
    "lakh": 100_000,
    "lakhs": 100_000,
    "lac": 100_000,
    "lacs": 100_000,
    "crore": 10_000_000,
    "crores": 10_000_000,
    "cr": 10_000_000,
    "cr.": 10_000_000,
    "thousand": 1_000,
    "k": 1_000,
    "million": 1_000_000,
    "mn": 1_000_000,
    "billion": 1_000_000_000,
    "bn": 1_000_000_000,
}


@dataclass(frozen=True)
class MoneyParse:
    inr: int
    """Integer rupees. Paise rounding handled by truncation."""

    raw: str
    confidence: float


def parse_inr(text: str) -> MoneyParse | None:
    """Best-effort 'amount in INR' parser.

    Examples it should accept:
      * "Rs. 5 crore"           → 50_000_000
      * "₹5,00,00,000"          → 50_000_000
      * "INR 50000000"          → 50_000_000
      * "5.0 Cr"                → 50_000_000
      * "Five crore"            → 50_000_000
      * "Rs. 12.34 lakh"        → 1_234_000
      * "Rupees 4,50,000"        → 450_000
      * "USD 100,000"           → None  (not INR)

    Returns None when no plausible amount can be parsed. The confidence
    field is intentionally crude — it lets the caller weight ambiguous
    parses lower without dropping them.
    """
    if not text:
        return None
    raw = text.strip()
    lower = raw.lower()

    # Reject obvious non-INR currencies up-front.
    if re.search(r"\busd\b|\beur\b|\bgbp\b|\bjpy\b|\$|€|£|¥", raw, re.IGNORECASE):
        return None

    # Strip currency markers.
    cleaned = re.sub(r"(?i)(rupees?|rs\.?|inr|₹)", " ", raw).strip()
    cleaned_lower = cleaned.lower()

    # Word-form first: "five crore", "two lakh fifty thousand"
    if any(u in cleaned_lower for u in _UNIT_MULTIPLIERS_INR) and not _DECIMAL.search(cleaned):
        words = re.findall(r"[a-zA-Z\.]+", cleaned_lower)
        total, current = 0, 0
        for w in words:
            if w in _WORD_TO_NUM:
                current += _WORD_TO_NUM[w]
            elif w in _UNIT_MULTIPLIERS_INR:
                if current == 0:
                    current = 1
                total += current * _UNIT_MULTIPLIERS_INR[w]
                current = 0
        total += current
        if total > 0:
            return MoneyParse(inr=total, raw=raw, confidence=0.7)

    # Mixed: "Rs. 5 crore" / "5.0 Cr" / "12.5 lakhs"
    m_unit = re.search(r"([\d,]+(?:\.\d+)?)\s*([a-zA-Z\.]+)", cleaned_lower)
    if m_unit:
        num_str = m_unit.group(1).replace(",", "")
        unit = m_unit.group(2).rstrip(".s").lower()
        unit_full = m_unit.group(2).lower()
        try:
            num = float(num_str)
        except ValueError:
            num = None
        mult = _UNIT_MULTIPLIERS_INR.get(unit_full) or _UNIT_MULTIPLIERS_INR.get(unit)
        if num is not None and mult is not None:
            return MoneyParse(inr=int(round(num * mult)), raw=raw, confidence=0.95)

    # Plain number, possibly Indian-grouped: "5,00,00,000" or "50000000".
    m_plain = _NUMBER_WITH_COMMAS.search(cleaned)
    if m_plain:
        ns = m_plain.group(0).replace(",", "")
        try:
            v = float(ns)
        except ValueError:
            return None
        if v <= 0:
            return None
        return MoneyParse(inr=int(round(v)), raw=raw, confidence=0.6 if "," not in m_plain.group(0) else 0.9)

    return None


# ─── Financial year ───────────────────────────────────────────────────────


_FY_PATTERNS = [
    re.compile(r"(?i)\bFY\s*(\d{4})\s*[-/]\s*(\d{2,4})\b"),
    re.compile(r"(?i)\b(?:financial\s+year|fy)\s*(\d{2})\s*[-/]\s*(\d{2})\b"),
    re.compile(r"(?i)\bAY\s*(\d{4})\s*[-/]\s*(\d{2,4})\b"),
    re.compile(r"\b(\d{4})\s*[-/]\s*(\d{2,4})\b"),
]


def parse_fy(text: str) -> str | None:
    """Canonicalise to 'YYYY-YY' (e.g. '2023-24').

    Recognises:
      FY 23-24 / FY 2023-24 / FY 2023-2024 / 2023-24 / 2023-2024 /
      AY 2024-25 (which corresponds to FY 2023-24)
    """
    if not text:
        return None
    for pat in _FY_PATTERNS:
        m = pat.search(text)
        if not m:
            continue
        a, b = m.group(1), m.group(2)
        is_ay = bool(re.search(r"(?i)\bAY\b", text[: m.end()]))
        try:
            ai = int(a)
            bi = int(b)
        except ValueError:
            continue
        # Expand 2-digit years.
        if ai < 100:
            ai += 2000
        if bi < 100:
            bi += 2000
        # Sanity: years should be within reasonable range.
        if not (1990 <= ai <= 2100 and 1990 <= bi <= 2100):
            continue
        if is_ay:
            ai, bi = ai - 1, bi - 1
        if bi - ai != 1:
            # Non-adjacent → not an FY span.
            continue
        return f"{ai}-{str(bi)[-2:]}"
    return None


def fy_end_year(fy: str) -> int | None:
    """Return the calendar year on 31-Mar of FY YYYY-YY."""
    m = re.match(r"^(\d{4})-(\d{2})$", fy)
    if not m:
        return None
    return int(m.group(1)) + 1


# ─── Date ─────────────────────────────────────────────────────────────────


_DATE_FORMATS = [
    "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y",
    "%d %b %Y", "%d %B %Y", "%b %d, %Y", "%B %d, %Y",
    "%d %b, %Y", "%d %B, %Y",
]


def parse_date_iso(text: str) -> str | None:
    """Best-effort date → ISO-8601 string ('YYYY-MM-DD').

    Returns None when no date is recognisable. We try several common Indian
    formats first (DD-MM-YYYY, etc.) before falling back to ISO.
    """
    if not text:
        return None
    s = text.strip().rstrip(".,")
    for fmt in _DATE_FORMATS:
        try:
            d = datetime.strptime(s, fmt).date()
            return d.isoformat()
        except ValueError:
            continue
    # Loose match: '15 April 2026' / '01-Apr-2026'
    m = re.search(r"(\d{1,2})[ \-/](\w{3,9})[ \-/](\d{2,4})", s)
    if m:
        for fmt in ("%d %b %Y", "%d %B %Y", "%d-%b-%Y", "%d-%B-%Y"):
            try:
                d = datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}", fmt).date()
                return d.isoformat()
            except ValueError:
                continue
    return None


def date_in_window(iso_date: str, *, last_n_years: int, today: date | None = None) -> bool:
    today = today or date.today()
    try:
        d = date.fromisoformat(iso_date)
    except ValueError:
        return False
    delta_days = (today - d).days
    return 0 <= delta_days <= last_n_years * 366


# ─── Identity / regulatory IDs ────────────────────────────────────────────


GSTIN_RE = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]{3}$")
PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
CIN_RE = re.compile(r"^[LU][0-9]{5}[A-Z]{2}[0-9]{4}[A-Z]{3}[0-9]{6}$")
UDIN_RE = re.compile(r"^\d{2}[A-Z0-9]{6}[A-Z0-9]{10}$")


def normalise_gstin(s: str) -> str | None:
    if not s:
        return None
    cleaned = re.sub(r"\s+", "", s).upper()
    return cleaned if GSTIN_RE.match(cleaned) else None


def normalise_pan(s: str) -> str | None:
    if not s:
        return None
    cleaned = re.sub(r"\s+", "", s).upper()
    return cleaned if PAN_RE.match(cleaned) else None


def normalise_cin(s: str) -> str | None:
    if not s:
        return None
    cleaned = re.sub(r"\s+", "", s).upper()
    return cleaned if CIN_RE.match(cleaned) else None


def normalise_udin(s: str) -> str | None:
    if not s:
        return None
    cleaned = re.sub(r"[\s\-]", "", s).upper()
    return cleaned if UDIN_RE.match(cleaned) else None


# ─── Entity name canonicalisation ─────────────────────────────────────────


_LEGAL_SUFFIX_RE = re.compile(
    r"(?i)\b(pvt\.?\s*ltd\.?|private\s+limited|ltd\.?|limited|llp\.?|inc\.?|co\.?)\b"
)


def canonical_entity_name(name: str) -> str:
    """Lowercase, strip legal suffixes + extra whitespace; for fuzzy matching.

    NOT a primary key — when we have a CIN we use that. This is a fallback.
    """
    if not name:
        return ""
    s = _LEGAL_SUFFIX_RE.sub("", name)
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s

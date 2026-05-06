"""Document classifier + dispatcher.

Routes an uploaded file to the right parser:
  * Path A — Typed PDF       → `pdf_typed.parse`
  * Path B — Scanned PDF     → `pdf_scanned.parse`
  * Path C — Photo / Stamp   → `photo.parse`
  * Path D — Word            → `docx.parse`
  * Path E — Excel           → `xlsx.parse`

Outputs a list of `PageBlock` carrying full provenance (page + bbox + source
text + per-block confidence). The Excavator agent then turns blocks into
typed `EvidenceNode` records.
"""

from __future__ import annotations

import hashlib
import io
import logging
import mimetypes
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import pypdf

log = logging.getLogger(__name__)


class DocumentClass(StrEnum):
    TYPED_PDF = "typed_pdf"
    SCANNED_PDF = "scanned_pdf"
    PHOTO = "photo"
    DOCX = "docx"
    XLSX = "xlsx"
    UNSUPPORTED = "unsupported"


@dataclass(slots=True)
class PageBlock:
    """A single span of text from a single page, with provenance."""

    page: int
    text: str
    bbox: tuple[float, float, float, float]
    ocr_conf: float = 1.0
    extractor: str = "pdfplumber"
    source_text_sha256: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


# ─── Public API ───────────────────────────────────────────────────────────


def classify(filename: str, data: bytes) -> DocumentClass:
    """Best-effort classification using filename + content sniff."""
    name = filename.lower()
    if name.endswith(".pdf"):
        return _classify_pdf(data)
    if name.endswith(".docx"):
        return DocumentClass.DOCX
    if name.endswith(".xlsx") or name.endswith(".xls"):
        return DocumentClass.XLSX
    if name.endswith((".jpg", ".jpeg", ".png", ".webp", ".heic", ".tif", ".tiff")):
        return DocumentClass.PHOTO

    mime, _ = mimetypes.guess_type(filename)
    if mime == "application/pdf":
        return _classify_pdf(data)
    if mime and mime.startswith("image/"):
        return DocumentClass.PHOTO
    return DocumentClass.UNSUPPORTED


def parse(filename: str, data: bytes) -> tuple[DocumentClass, list[PageBlock]]:
    """Classify and parse in one call. Returns (class, blocks)."""
    cls = classify(filename, data)

    # Lazy imports keep heavy OCR / image libs out of the import path of the
    # FastAPI startup when those modules aren't actually exercised.
    if cls == DocumentClass.TYPED_PDF:
        from pramaan.ingestion.pdf_typed import parse_typed_pdf

        return cls, parse_typed_pdf(data)
    if cls == DocumentClass.SCANNED_PDF:
        from pramaan.ingestion.pdf_scanned import parse_scanned_pdf

        return cls, parse_scanned_pdf(data)
    if cls == DocumentClass.PHOTO:
        from pramaan.ingestion.photo import parse_photo

        return cls, parse_photo(filename, data)
    if cls == DocumentClass.DOCX:
        from pramaan.ingestion.docx import parse_docx

        return cls, parse_docx(data)
    if cls == DocumentClass.XLSX:
        from pramaan.ingestion.xlsx import parse_xlsx

        return cls, parse_xlsx(data)

    log.warning("unsupported document type: %s", filename)
    return cls, []


# ─── Internals ────────────────────────────────────────────────────────────


def _classify_pdf(data: bytes) -> DocumentClass:
    """Typed vs scanned decided by text density across the first few pages."""
    try:
        reader = pypdf.PdfReader(io.BytesIO(data))
    except Exception:
        return DocumentClass.UNSUPPORTED

    n_pages = len(reader.pages)
    if n_pages == 0:
        return DocumentClass.UNSUPPORTED

    sample = min(3, n_pages)
    total_chars = 0
    for i in range(sample):
        try:
            total_chars += len((reader.pages[i].extract_text() or "").strip())
        except Exception:
            continue

    # Empirical threshold: <50 visible chars / page on a 3-page sample → likely scanned.
    if total_chars / sample < 50:
        return DocumentClass.SCANNED_PDF
    return DocumentClass.TYPED_PDF


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

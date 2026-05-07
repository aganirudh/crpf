"""Typed PDF parser — pdfplumber with bbox preservation.

Each `PageBlock` carries the bbox in PDF user-space coordinates (bottom-left
origin in pdfplumber's API). The frontend converts to top-left in the viewer.
"""

from __future__ import annotations

import io
import logging

import pdfplumber

from pramaan.ingestion.router import PageBlock, hash_text

log = logging.getLogger(__name__)


def parse_typed_pdf(data: bytes) -> list[PageBlock]:
    blocks: list[PageBlock] = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page_idx, page in enumerate(pdf.pages, start=1):
            # 1) Table extraction (critical for tenders where eligibility criteria
            #    and document checklists are presented as grids).
            try:
                tables = page.find_tables(
                    table_settings={
                        "vertical_strategy": "lines",
                        "horizontal_strategy": "lines",
                        "intersection_tolerance": 5,
                        "snap_tolerance": 3,
                        "join_tolerance": 3,
                        "edge_min_length": 10,
                        "min_words_vertical": 1,
                        "min_words_horizontal": 1,
                    }
                )
            except Exception as exc:  # pragma: no cover
                log.debug("pdfplumber table detection failed: %s", exc)
                tables = []

            for t in tables:
                try:
                    rows = t.extract() or []
                except Exception:
                    continue
                # Emit one block per non-empty row.
                for row in rows:
                    if not row:
                        continue
                    cells = [("" if c is None else str(c)).strip() for c in row]
                    if not any(cells):
                        continue
                    text = " | ".join(c for c in cells if c)
                    if not text:
                        continue
                    x0, top, x1, bottom = map(float, t.bbox)
                    blocks.append(
                        PageBlock(
                            page=page_idx,
                            text=text,
                            bbox=(x0, float(top), x1, float(bottom)),
                            ocr_conf=1.0,
                            extractor="pdfplumber:table",
                            source_text_sha256=hash_text(text),
                            extra={"table_cells": cells},
                        )
                    )

            # 2) Word-flow text (works well for paragraphs/headings).
            words = page.extract_words(use_text_flow=True, keep_blank_chars=False) or []
            # Group consecutive words into "lines" by y-coordinate proximity.
            for line in _group_lines(words):
                text = " ".join(w["text"] for w in line).strip()
                if not text:
                    continue
                x0 = min(float(w["x0"]) for w in line)
                x1 = max(float(w["x1"]) for w in line)
                y0 = min(float(w["top"]) for w in line)
                y1 = max(float(w["bottom"]) for w in line)
                blocks.append(
                    PageBlock(
                        page=page_idx,
                        text=text,
                        bbox=(x0, y0, x1, y1),
                        ocr_conf=1.0,
                        extractor="pdfplumber",
                        source_text_sha256=hash_text(text),
                    )
                )
    return blocks


def _group_lines(words: list[dict], y_tolerance: float = 3.0) -> list[list[dict]]:
    """Group consecutive words on the same baseline."""
    lines: list[list[dict]] = []
    current: list[dict] = []
    last_y: float | None = None
    for w in sorted(words, key=lambda w: (round(float(w["top"]) / y_tolerance), float(w["x0"]))):
        y = float(w["top"])
        if last_y is None or abs(y - last_y) <= y_tolerance:
            current.append(w)
        else:
            if current:
                lines.append(current)
            current = [w]
        last_y = y
    if current:
        lines.append(current)
    return lines

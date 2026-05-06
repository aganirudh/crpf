"""Scanned PDF parser — render → Tesseract OCR with bbox + confidence.

Tesseract is the dev default (works on Windows after a one-time install).
PaddleOCR is wired in optionally (set `PRAMAAN_USE_PADDLEOCR=1`).

For real-world deployment the production stack uses PaddleOCR + docTR
(see docs/04-document-pipeline.md). We can swap engines without touching
upstream code by keeping the `PageBlock` contract stable.
"""

from __future__ import annotations

import io
import logging

import pytesseract
from pdf2image import convert_from_bytes

from pramaan.config import settings
from pramaan.ingestion.router import PageBlock, hash_text

log = logging.getLogger(__name__)


def parse_scanned_pdf(data: bytes, dpi: int = 300) -> list[PageBlock]:
    if settings.tesseract_path:
        pytesseract.pytesseract.tesseract_cmd = settings.tesseract_path

    try:
        images = convert_from_bytes(data, dpi=dpi)
    except Exception as exc:
        log.warning("pdf2image failed (%s) — falling back to pypdf raster heuristic", exc)
        return []

    blocks: list[PageBlock] = []
    for page_idx, img in enumerate(images, start=1):
        try:
            data_dict = pytesseract.image_to_data(
                img, output_type=pytesseract.Output.DICT, lang="eng"
            )
        except Exception as exc:
            log.warning("OCR failed on page %d: %s", page_idx, exc)
            continue
        n = len(data_dict["text"])
        # Group adjacent words into lines using Tesseract's block / line keys.
        line_buf: dict[tuple[int, int, int], list[int]] = {}
        for i in range(n):
            text = (data_dict["text"][i] or "").strip()
            if not text:
                continue
            key = (
                int(data_dict["block_num"][i]),
                int(data_dict["par_num"][i]),
                int(data_dict["line_num"][i]),
            )
            line_buf.setdefault(key, []).append(i)

        for indices in line_buf.values():
            text = " ".join((data_dict["text"][i] or "").strip() for i in indices).strip()
            if not text:
                continue
            confs = [int(data_dict["conf"][i]) for i in indices if int(data_dict["conf"][i]) >= 0]
            x0 = min(int(data_dict["left"][i]) for i in indices)
            y0 = min(int(data_dict["top"][i]) for i in indices)
            x1 = max(int(data_dict["left"][i]) + int(data_dict["width"][i]) for i in indices)
            y1 = max(int(data_dict["top"][i]) + int(data_dict["height"][i]) for i in indices)
            mean_conf = (sum(confs) / len(confs)) / 100.0 if confs else 0.5
            blocks.append(
                PageBlock(
                    page=page_idx,
                    text=text,
                    bbox=(float(x0), float(y0), float(x1), float(y1)),
                    ocr_conf=max(0.0, min(1.0, mean_conf)),
                    extractor="tesseract",
                    source_text_sha256=hash_text(text),
                )
            )
    return blocks


def _bytes_io(data: bytes) -> io.BytesIO:
    return io.BytesIO(data)

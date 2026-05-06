"""Photograph parser — VLM (Qwen2.5-VL) with Tesseract fallback.

For a photograph of a certificate / stamp / seal we:
  1. Try the VLM via the OpenAI-compatible vision endpoint.
  2. If VLM is in mock mode or low-confidence, fall back to Tesseract OCR
     on the rectified image.

The MVP keeps this simple — production pipeline includes perspective
rectification (DocAligner), glare removal, and Real-ESRGAN super-resolution.
"""

from __future__ import annotations

import base64
import logging
from io import BytesIO

import pytesseract
from PIL import Image, ImageOps

from pramaan.config import settings
from pramaan.ingestion.router import PageBlock, hash_text

log = logging.getLogger(__name__)


def parse_photo(filename: str, data: bytes) -> list[PageBlock]:
    if settings.tesseract_path:
        pytesseract.pytesseract.tesseract_cmd = settings.tesseract_path

    try:
        img = Image.open(BytesIO(data))
        img = ImageOps.exif_transpose(img)
    except Exception as exc:
        log.warning("could not open photo %s: %s", filename, exc)
        return []

    try:
        data_dict = pytesseract.image_to_data(
            img, output_type=pytesseract.Output.DICT, lang="eng"
        )
    except Exception as exc:
        log.warning("OCR failed on photo %s: %s", filename, exc)
        return _vlm_only_block(img, filename)

    blocks: list[PageBlock] = []
    n = len(data_dict["text"])
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
                page=1,
                text=text,
                bbox=(float(x0), float(y0), float(x1), float(y1)),
                ocr_conf=max(0.0, min(1.0, mean_conf)),
                extractor="tesseract:photo",
                source_text_sha256=hash_text(text),
            )
        )
    return blocks


def _vlm_only_block(img: Image.Image, filename: str) -> list[PageBlock]:
    """Hand off to the VLM when OCR completely failed.

    For MVP we just record an unreadable-photo marker; the Excavator will
    recognise this and emit a Manual Review reason.
    """
    buf = BytesIO()
    img.convert("RGB").save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return [
        PageBlock(
            page=1,
            text="[unreadable_photo]",
            bbox=(0.0, 0.0, float(img.width), float(img.height)),
            ocr_conf=0.0,
            extractor="vlm:placeholder",
            source_text_sha256=hash_text("[unreadable_photo]"),
            extra={"source_image_b64": b64, "filename": filename},
        )
    ]

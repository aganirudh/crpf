"""Document understanding pipeline.

Spec: docs/04-document-pipeline.md

Public surface:
  * `classify(filename, data)` -> document class
  * `parse(filename, data)`    -> list of `PageBlock` with provenance
"""

from pramaan.ingestion.router import DocumentClass, PageBlock, classify, parse

__all__ = ["DocumentClass", "PageBlock", "classify", "parse"]

"""CriterionDSL — the typed contract between LLM extraction and Rego adjudication.

Spec: docs/03-criterion-dsl.md
"""

from pramaan.dsl.normalize import (
    canonical_entity_name,
    date_in_window,
    fy_end_year,
    normalise_cin,
    normalise_gstin,
    normalise_pan,
    normalise_udin,
    parse_date_iso,
    parse_fy,
    parse_inr,
)
from pramaan.dsl.types import (
    Constraint,
    Criterion,
    CriterionDSL,
    CriterionType,
    DocConstraint,
    EvidenceVocabularyEntry,
    ScalarConstraint,
    SetConstraint,
    TenderMeta,
    Window,
)

__all__ = [
    "Constraint",
    "Criterion",
    "CriterionDSL",
    "CriterionType",
    "DocConstraint",
    "EvidenceVocabularyEntry",
    "ScalarConstraint",
    "SetConstraint",
    "TenderMeta",
    "Window",
    "canonical_entity_name",
    "date_in_window",
    "fy_end_year",
    "normalise_cin",
    "normalise_gstin",
    "normalise_pan",
    "normalise_udin",
    "parse_date_iso",
    "parse_fy",
    "parse_inr",
]

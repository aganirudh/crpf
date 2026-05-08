"""CriterionDSL — Pydantic types.

Mirrors `docs/03-criterion-dsl.md` exactly. These types are the schema the
Cartographer is constrained to emit (via Outlines/Instructor) and the schema
the compiler-to-Rego consumes.

Design rules:
  * Every literal value lives here, in code, not in prompt text.
  * Every constraint type is closed (sealed union); the LLM cannot invent shapes.
  * `escape_hatch=True` is the only legal way to express something the grammar
    cannot model — and it forces Manual Review during adjudication.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# ─── Enumerations ──────────────────────────────────────────────────────────


CriterionType = Literal["technical", "financial", "compliance", "certification", "documentary"]


ScalarOp = Literal[
    ">", ">=", "<", "<=", "==", "!=", "regex_match", "exists",
    "regex_match + active_on(today)",
    "exists + valid_on(today)",
    "exists + valid_on(today) + accredited_by_iaf_mla",
]


SetAggregator = Literal["any", "all", "mean", "max"]


SetOp = Literal[
    "count >=", "count ==", "count >", "count <=",
    "sum >=", "sum >", "max >=", "min >=",
]


DocOp = Literal["exists", "valid_on(today)", "issued_after"]


# ─── Sub-shapes ────────────────────────────────────────────────────────────


class Window(BaseModel):
    """A temporal scope on which a constraint applies.

    Exactly one of `last_n_fy`, `last_n_years`, or `between` must be set.
    `aggregator` controls how multiple in-window observations combine.
    """

    model_config = ConfigDict(extra="ignore")

    last_n_fy: int | None = Field(default=None, ge=1, le=20)
    last_n_years: int | None = Field(default=None, ge=1, le=20)
    between: tuple[str, str] | None = None  # ISO-8601 dates
    aggregator: SetAggregator = "any"


class TextSource(BaseModel):
    """Where in the tender did this criterion come from?"""

    model_config = ConfigDict(extra="ignore")

    page: int = Field(ge=1)
    bbox: tuple[float, float, float, float]


class CrossCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")

    against: str
    tolerance_pct: float = Field(default=5.0, ge=0.0, le=100.0)


# ─── Constraint variants ──────────────────────────────────────────────────


class ScalarConstraint(BaseModel):
    """A single-value comparison."""

    model_config = ConfigDict(extra="ignore")

    kind: Literal["scalar"] = "scalar"
    field: str
    op: ScalarOp
    value: int | float | str | None = None  # None for "exists"-style ops
    unit: str | None = None
    window: Window | None = None


class SetConstraint(BaseModel):
    """An aggregate over a filtered set (e.g. "at least 3 similar projects")."""

    model_config = ConfigDict(extra="ignore")

    kind: Literal["set"] = "set"
    field: str
    filter: dict[str, Any] = Field(default_factory=dict)
    op: SetOp
    value: int | float


class DocConstraint(BaseModel):
    """A 'this document must exist (and be valid)' check."""

    model_config = ConfigDict(extra="ignore")

    kind: Literal["doc"] = "doc"
    field: str
    op: DocOp = "exists"
    issuer: str | None = None  # regex over issuer name


Constraint = Annotated[
    ScalarConstraint | SetConstraint | DocConstraint,
    Field(discriminator="kind"),
]


# ─── Criterion ────────────────────────────────────────────────────────────


class Criterion(BaseModel):
    """One eligibility criterion, fully typed and machine-evaluable."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(pattern=r"^C\d+$")
    type: CriterionType
    mandatory: bool = True
    mandatory_confidence: float = Field(ge=0.0, le=1.0, default=0.95)

    text: str
    text_source: TextSource | None = None

    constraint: Constraint | None = None
    """May be None when escape_hatch=True."""

    evidence_required: list[str] = Field(default_factory=list)
    validators: list[str] = Field(default_factory=list)
    cross_check: list[CrossCheck] = Field(default_factory=list)

    escape_hatch: bool = False
    """True when the criterion cannot be expressed in this DSL grammar.
    Such criteria always route to Manual Review during adjudication."""
    escape_hatch_text: str | None = None

    notes: str | None = None


# ─── Vocabulary ───────────────────────────────────────────────────────────


class EvidenceVocabularyEntry(BaseModel):
    """A canonical evidence-document name plus its tender-specific aliases."""

    model_config = ConfigDict(extra="ignore")

    aliases: list[str] = Field(default_factory=list)
    expected_fields: list[str] = Field(default_factory=list)


# ─── Top-level ────────────────────────────────────────────────────────────


class TenderMeta(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    source_sha256: str
    classification: str | None = None
    language: str = "en"
    pages: int | None = None
    extracted_by: dict[str, Any] | None = None
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None


class CriterionDSL(BaseModel):
    """Top-level DSL document (matches docs/03-criterion-dsl.md)."""

    model_config = ConfigDict(extra="ignore")

    dsl_version: Literal["v1"] = "v1"
    tender: TenderMeta
    criteria: list[Criterion] = Field(default_factory=list)
    evidence_vocabulary: dict[str, EvidenceVocabularyEntry] = Field(default_factory=dict)

    def by_id(self, criterion_id: str) -> Criterion:
        for c in self.criteria:
            if c.id == criterion_id:
                return c
        raise KeyError(f"criterion {criterion_id!r} not found in DSL")

    def mandatory_ids(self) -> list[str]:
        return [c.id for c in self.criteria if c.mandatory]

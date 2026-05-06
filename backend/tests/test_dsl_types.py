"""Round-trip tests for the CriterionDSL types."""

from __future__ import annotations

from pramaan.dsl.types import CriterionDSL
from pramaan.llm.mock import _sample_criterion_dsl


def test_sample_dsl_validates_and_round_trips():
    dsl = _sample_criterion_dsl(CriterionDSL)
    assert isinstance(dsl, CriterionDSL)
    assert dsl.dsl_version == "v1"
    assert {c.id for c in dsl.criteria} == {"C1", "C2", "C3", "C4"}

    # Re-serialise → re-validate to catch any schema drift.
    again = CriterionDSL.model_validate(dsl.model_dump(mode="json"))
    assert again == dsl


def test_mandatoriness_helpers():
    dsl = _sample_criterion_dsl(CriterionDSL)
    assert dsl.mandatory_ids() == ["C1", "C2", "C3", "C4"]


def test_constraint_discriminator():
    dsl = _sample_criterion_dsl(CriterionDSL)
    c1 = dsl.by_id("C1")
    c2 = dsl.by_id("C2")
    assert c1.constraint is not None and c1.constraint.kind == "scalar"
    assert c2.constraint is not None and c2.constraint.kind == "set"

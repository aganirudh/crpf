"""Agents — narrow contracts, narrow purposes.

  * Cartographer — tender PDF → CriterionDSL
  * Excavator    — bidder bundle → EvidenceGraph (W3)
  * Adjudicator  — CriterionDSL + EvidenceGraph → Verdicts (W4, OPA-backed)
  * Skeptic      — adversarial review of draft verdicts (W4)
  * Scribe       — assembles + signs the ReportBundle (W6)
  * Integrity    — cross-bidder analytics (W6)
"""

from pramaan.agents.adjudicator import Adjudicator, AdjudicatorVerdict
from pramaan.agents.cartographer import Cartographer, CartographerOutput
from pramaan.agents.evidence_graph import (
    EvidenceGraphView,
    FieldAggregate,
    build_evidence_graph,
)
from pramaan.agents.excavator import (
    ExcavateBidderResult,
    ExcavateDocumentResult,
    Excavator,
)

from pramaan.agents.skeptic import Skeptic, SkepticResponse

__all__ = [
    "Adjudicator",
    "AdjudicatorVerdict",
    "Cartographer",
    "CartographerOutput",
    "EvidenceGraphView",
    "ExcavateBidderResult",
    "ExcavateDocumentResult",
    "Excavator",
    "FieldAggregate",
    "Skeptic",
    "SkepticResponse",
    "build_evidence_graph",
]

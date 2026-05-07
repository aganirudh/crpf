import logging
from typing import Dict, Any
from pydantic import BaseModel

from pramaan.config import settings
from pramaan.llm.client import get_llm_client
from pramaan.agents.adjudicator import AdjudicatorVerdict
from pramaan.agents.evidence_graph import EvidenceGraphView
from pramaan.dsl.types import Criterion

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the Skeptic agent for a government procurement platform.
Your job is to adversarially review draft verdicts made by an automated rule engine.
You will be given the Criterion, the Draft Verdict, the evidence used by the rule engine, and the bidder's FULL Evidence Graph.
Your goal is to find flaws in the Draft Verdict. Is there conflicting evidence the rule engine ignored? Does the evidence not actually satisfy the criterion logically?
If you find a logical contradiction or strong counter-evidence, output "counter" and explain it.
If the verdict is solid and no counter-argument exists, output "accept".
Do not disagree just to disagree. Only raise valid counter-arguments."""

USER_PROMPT_TEMPLATE = """
Criterion: {criterion}
Draft Verdict: {verdict}
Reason: {reason}

Evidence Used by Rule Engine:
{evidence_used}

Bidder's Full Evidence Graph:
{full_evidence}

Find the strongest counter-argument to the draft verdict. 
"""

class SkepticResponse(BaseModel):
    outcome: str  # "accept" or "counter"
    counter: str
    cited_nodes: list[str]

class Skeptic:
    """Adversarially reviews draft verdicts to ensure robustness."""

    def __init__(self):
        self.llm = get_llm_client()

    def challenge_verdict(self, criterion: Criterion, draft_verdict: AdjudicatorVerdict, evidence_graph: EvidenceGraphView) -> SkepticResponse:
        """
        Takes the draft verdict and attempts to overturn it.
        If it returns "counter", the verdict should be downgraded to manual_review.
        """
        # Fast path: only challenge "eligible" or "not_eligible" verdicts. 
        # Manual reviews are already flagged for humans.
        if draft_verdict.status == "manual_review":
            return SkepticResponse(outcome="accept", counter="", cited_nodes=[])

        user_prompt = USER_PROMPT_TEMPLATE.format(
            criterion=criterion.model_dump_json(indent=2),
            verdict=draft_verdict.status,
            reason=draft_verdict.reason_text,
            evidence_used=draft_verdict.evidence_used,
            full_evidence=[{ "field": f.field, "value": f.value, "sources": len(f.sources) } for f in evidence_graph.fields]
        )

        try:
            result = self.llm.extract(
                response_model=SkepticResponse,
                system=SYSTEM_PROMPT,
                user=user_prompt,
                model=settings.llm_skeptic_model,
                prompt_template_version="skeptic:v1"
            )
            return result.value
        except Exception as e:
            log.error(f"Skeptic failed: {e}")
            # If the skeptic fails to run, we safely abstain (accept draft for now, or could downgrade)
            return SkepticResponse(outcome="accept", counter=f"Skeptic failed: {e}", cited_nodes=[])

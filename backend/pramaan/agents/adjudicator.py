import uuid
from typing import Any, Dict, List, Optional
import httpx
from pydantic import BaseModel
from sqlalchemy.orm import Session

from pramaan.config import settings
from pramaan.db.models import Bidder
from pramaan.dsl.types import Criterion, CriterionDSL
from pramaan.agents.evidence_graph import EvidenceGraphView, FieldAggregate

class AdjudicatorVerdict(BaseModel):
    criterion_id: str
    status: str  # "eligible", "not_eligible", "manual_review"
    reason_tag: str
    reason_text: str
    evidence_used: List[Dict[str, Any]]
    policy: Dict[str, str]


class Adjudicator:
    """Evaluates criteria against the EvidenceGraph using Open Policy Agent (Rego)."""

    def __init__(self, session: Session):
        self.session = session
        self.opa_url = settings.opa_url.rstrip("/")

    def evaluate_criterion(self, criterion: Criterion, evidence_graph: EvidenceGraphView) -> AdjudicatorVerdict:
        """Evaluate a single criterion via OPA."""
        
        # Prepare input
        evidence_list = []
        evidence_used = []
        
        if criterion.constraint and hasattr(criterion.constraint, 'field'):
            field_name = criterion.constraint.field
            aggregates = evidence_graph.by_field(field_name)
            
            for agg in aggregates:
                evidence_list.append({
                    "field": agg.field,
                    "value": agg.value,
                    "final_conf": agg.final_conf,
                    "cross_doc_disagreement": agg.cross_doc_disagreement,
                })
                # Add all sources to evidence_used for provenance
                for source in agg.sources:
                    evidence_used.append({
                        "node_id": str(source.node_id),
                        "doc": str(source.document_id),
                        "page": source.page,
                        "bbox": source.bbox,
                        "value": source.value,
                        "conf": source.final_conf
                    })
        
        opa_input = {
            "input": {
                "criterion": criterion.model_dump(),
                "evidence": evidence_list
            }
        }

        # Query OPA
        try:
            # We assume the policy is loaded at /v1/data/eligibility/adjudicator
            # In a real setup, we would ensure the policy is pushed to OPA at startup
            response = httpx.post(f"{self.opa_url}/v1/data/eligibility/adjudicator", json=opa_input, timeout=5.0)
            if response.status_code == 200:
                result = response.json().get("result", {})
                verdict = result.get("verdict", "manual_review")
                reason_tag = result.get("reason_tag", "opa_eval_error")
                reason_text = result.get("reason_text", "No detailed reason provided by OPA.")
            else:
                verdict = "manual_review"
                reason_tag = "opa_connection_error"
                reason_text = f"Failed to reach OPA sidecar. Status: {response.status_code}"
                
        except Exception as e:
            # Fallback to manual review if OPA is down
            verdict = "manual_review"
            reason_tag = "opa_connection_error"
            reason_text = f"Exception calling OPA: {str(e)}"
            
        return AdjudicatorVerdict(
            criterion_id=criterion.id,
            status=verdict,
            reason_tag=reason_tag,
            reason_text=reason_text,
            evidence_used=evidence_used,
            policy={
                "rego_module": "eligibility.adjudicator",
                "opa_version": "unknown"
            }
        )

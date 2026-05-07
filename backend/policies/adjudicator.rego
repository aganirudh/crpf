package eligibility.adjudicator

# Input shape:
# {
#   "criterion": { "id": "C1", "constraint": { "kind": "scalar", "field": "annual_turnover", "op": ">=", "value": 50000000 }, "escape_hatch": false },
#   "evidence": [ 
#      { "field": "annual_turnover", "value": 51000000, "final_conf": 0.85, "cross_doc_disagreement": false, "sources": [...] }
#   ]
# }

default verdict = "manual_review"
default reason_tag = "unhandled_criterion_kind"
default reason_text = "The criterion constraint is not fully supported by the rule engine."

confidence_threshold := 0.80

# Helper to find evidence for the criterion's field
evidence_for_field = e {
    some i
    e := input.evidence[i]
    e.field == input.criterion.constraint.field
}

# 1. Escape Hatch -> always manual review
verdict = "manual_review" {
    input.criterion.escape_hatch == true
}

reason_tag = "criterion_not_machine_evaluable" {
    input.criterion.escape_hatch == true
}

reason_text = "Criterion is marked as not machine evaluable. Manual review required." {
    input.criterion.escape_hatch == true
}

# 2. Missing Evidence -> manual review (let officer decide if it's Not Eligible)
verdict = "manual_review" {
    input.criterion.escape_hatch == false
    not evidence_for_field
}

reason_tag = "evidence_missing" {
    input.criterion.escape_hatch == false
    not evidence_for_field
}

reason_text = "No evidence found in the bidder's documents for the required field." {
    input.criterion.escape_hatch == false
    not evidence_for_field
}

# 3. Evidence has low confidence -> manual review
verdict = "manual_review" {
    input.criterion.escape_hatch == false
    e := evidence_for_field
    e.final_conf < confidence_threshold
}

reason_tag = "evidence_low_confidence" {
    input.criterion.escape_hatch == false
    e := evidence_for_field
    e.final_conf < confidence_threshold
}

reason_text = sprintf("Evidence was extracted but confidence is low (%.2f < %.2f).", [evidence_for_field.final_conf, confidence_threshold]) {
    input.criterion.escape_hatch == false
    e := evidence_for_field
    e.final_conf < confidence_threshold
}

# 4. Evidence has cross-document disagreement -> manual review
verdict = "manual_review" {
    input.criterion.escape_hatch == false
    e := evidence_for_field
    e.cross_doc_disagreement == true
}

reason_tag = "cross_doc_disagreement" {
    input.criterion.escape_hatch == false
    e := evidence_for_field
    e.cross_doc_disagreement == true
}

reason_text = "Multiple documents provide conflicting values for this field." {
    input.criterion.escape_hatch == false
    e := evidence_for_field
    e.cross_doc_disagreement == true
}

# 5. Scalar Constraints (>=, <=, >, <, ==)
# Only applies if we have evidence, confidence is high, and no disagreement.

valid_evidence {
    e := evidence_for_field
    e.final_conf >= confidence_threshold
    e.cross_doc_disagreement == false
}

verdict = "eligible" {
    input.criterion.escape_hatch == false
    input.criterion.constraint.kind == "scalar"
    valid_evidence
    e := evidence_for_field
    
    # Evaluate operator
    input.criterion.constraint.op == ">="
    e.value >= input.criterion.constraint.value
}

verdict = "not_eligible" {
    input.criterion.escape_hatch == false
    input.criterion.constraint.kind == "scalar"
    valid_evidence
    e := evidence_for_field
    
    input.criterion.constraint.op == ">="
    e.value < input.criterion.constraint.value
}

verdict = "eligible" {
    input.criterion.escape_hatch == false
    input.criterion.constraint.kind == "scalar"
    valid_evidence
    e := evidence_for_field
    
    input.criterion.constraint.op == "=="
    e.value == input.criterion.constraint.value
}

verdict = "not_eligible" {
    input.criterion.escape_hatch == false
    input.criterion.constraint.kind == "scalar"
    valid_evidence
    e := evidence_for_field
    
    input.criterion.constraint.op == "=="
    e.value != input.criterion.constraint.value
}

# Doc constraints (exists)
verdict = "eligible" {
    input.criterion.escape_hatch == false
    input.criterion.constraint.kind == "doc"
    valid_evidence
}

# Fallback reason text for successful scalar evaluations
reason_tag = "evaluated_scalar" {
    input.criterion.escape_hatch == false
    input.criterion.constraint.kind == "scalar"
    valid_evidence
}

reason_text = sprintf("Value %v evaluated against constraint %v %v", [evidence_for_field.value, input.criterion.constraint.op, input.criterion.constraint.value]) {
    input.criterion.escape_hatch == false
    input.criterion.constraint.kind == "scalar"
    valid_evidence
}

reason_tag = "evaluated_doc" {
    input.criterion.escape_hatch == false
    input.criterion.constraint.kind == "doc"
    valid_evidence
}

reason_text = "Required document exists and is valid." {
    input.criterion.escape_hatch == false
    input.criterion.constraint.kind == "doc"
    valid_evidence
}

from typing import Literal
from graph.state import ClaimState

Route = Literal[
    "approve",
    "reject",
    "human_review",
    "request_information"
]

HIGH_VALUE_THRESHOLD = 500_000

def route_claim(state: ClaimState) -> Route:
    """Determine the next workflow branch from verification results."""

    documents = state.get("document_result", {})
    eligibility = state.get("eligibility_result", {})
    fraud = state.get("fraud_results", {})

    # A confirmed eligibility failure takes priority.
    if eligibility.get("status") == 'ineligible':
        return "reject"

    # Incomplete evidence should normally be requested.
    if(
        documents.get("status") != "verified"
        or eligibility.get("status") != "eligible"
        or fraud.get("risk_level") not in ('low', 'medium')
        or fraud.get('requrires_review', False)
        or state.get("claim_amount", 0) > HIGH_VALUE_THRESHOLD
    ):
        return "human_review"

    # Approve only when all mandatory checks pass.
    if(
        documents.get("status") == "verified"
        and eligibility.get("status") == "eligible"
        and fraud.get("risk_level") == "low"
        and not fraud.get("requires_review", False)
    ):
        return 'approve'

    # Fail safely if the evidence is inconclusive.
    return "human_review"

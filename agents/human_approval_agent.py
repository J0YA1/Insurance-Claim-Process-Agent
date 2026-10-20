
from langgraph.types import interrupt

from graph.state import ClaimState


ALLOWED_DECISIONS = {
    "approve",
    "reject",
    "request_information",
}


def human_approval_agent(state: ClaimState) -> dict:
    """Pause the graph and collect a human review decision."""

    review_request = {
        "claim_id": state.get("claim_id", "N/A"),
        "claim_amount": state.get("claim_amount", 0),
        "claim_summary": state.get("claim_summary", ""),
        "decision_reasons": state.get("decision_reasons", []),
        "allowed_decisions": sorted(ALLOWED_DECISIONS),
    }

    review = interrupt(review_request)

    if not isinstance(review, dict):
        raise ValueError("Reviewer response must be a dictionary.")

    decision = review.get("decision")

    if decision not in ALLOWED_DECISIONS:
        raise ValueError("Invalid human review decision.")

    return {
        "reviewer_decision": decision,
        "reviewer_notes": str(review.get("notes", "")),
    }

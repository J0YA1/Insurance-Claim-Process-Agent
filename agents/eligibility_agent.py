
from datetime import date

from graph.state import ClaimState


def eligibility_check_agent(state: ClaimState) -> dict:
    """Evaluate basic insurance policy eligibility."""

    try:
        incident_date = date.fromisoformat(state["incident_date"])
        policy_start = date.fromisoformat(state["policy_start_date"])
        policy_end = date.fromisoformat(state["policy_end_date"])
    except (KeyError, TypeError, ValueError):
        return {
            "eligibility_result": {
                "status": "uncertain",
                "policy_active": None,
                "coverage_available": None,
                "issues": ["Policy or incident dates are missing or invalid."],
            }
        }

    # Validate the policy period against the incident date.
    if incident_date < policy_start or incident_date > policy_end:
        return {
            "eligibility_result": {
                "status": "ineligible",
                "policy_active": False,
                "coverage_available": False,
                "issues": [
                    "Incident date falls outside the policy period."
                ],
            }
        }

    if state.get("coverage_available") is not True:
        return {
            "eligibility_result": {
                "status": "ineligible",
                "policy_active": True,
                "coverage_available": False,
                "issues": ["Required coverage is unavailable."],
            }
        }

    amount = state.get("claim_amount", 0)
    limit = state.get("coverage_limit", 0)

    if (
        not isinstance(amount, (int, float))
        or isinstance(amount, bool)
        or not isinstance(limit, (int, float))
        or isinstance(limit, bool)
        or amount <= 0
        or limit <= 0
    ):
        return {
            "eligibility_result": {
                "status": "uncertain",
                "policy_active": True,
                "coverage_available": True,
                "issues": ["Claim amount or coverage limit is invalid."],
            }
        }

    return {
        "eligibility_result": {
            "status": "eligible",
            "policy_active": True,
            "coverage_available": True,
            "eligible_amount": min(float(amount), float(limit)),
            "issues": [],
        }
    }

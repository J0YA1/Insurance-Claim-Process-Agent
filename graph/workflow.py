from datetime import date

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import interrupt

from graph.state import ClaimState
from graph.routing import route_claim


from agents.document_agent import document_verification_agent
from agents.eligibility_agent import eligibility_check_agent
from agents.fraud_agent import fraud_detection_agent
from agents.summary_agent import claim_summary_agent
from agents.human_approval_agent import human_approval_agent


#Document verfication agent

def document_verification_agent(state: ClaimState) -> dict:
    required = state.get('required_documents',[])
    provided = state.get('provided_documents', [])

    missing = sorted(set(required) - set(provided))

    if missing:
        status = 'missing'

    else:
        status = 'verified'

    return {
        "document_result":{
            "status" : status,
            "missing_documents": missing,
            "issues": [],
        }
    }

# Eligibility check Agent

def eligibility_check_agent(state: ClaimState) -> dict:
    try:
        incident_date = date.fromisoformat(state['incident_date'])
        start_date = date.fromisoformat(state['policy_start_date'])
        end_date = date.fromisoformat(state['policy_end_date'])

    except (KeyError, TypeError, ValueError):
        return {
            "eligibility_result":{
                "status": "uncertain",
                "issues": ["Missing or invalid policy dates."],
            }
        }

    if incident_date < start_date  or incident_date > end_date:
        return {
            "eligibility_result":{
                "status": 'ineligible',
                "issues": [
                    "incident date falls outside the policy period"
                ],
            }
        }

    if not state.get('coverage_available', False):
        return {
            "eligibility_resutl": {
                "status" : "ineligible",
                "issues": ["Required coverage is unavailable"],
            }
        }

    claim_amount = state.get('claim_amount', 0)
    coverage_limit = state.get('coverage_limit', 0)

    if claim_amount <= 0 or coverage_limit <= 0:
        return {
            "eligibility_result" : {
                'status': "uncertain",
                'issues': ["Claim amount or coverage limit is invalid."],
            }
        }

    return {
        "eligibility_result": {
            "status" : "eligible",
            "eligible_amount": min(claim_amount, coverage_limit),
            "issues": [],
        }
    }


# Fraud detection agent

def fraud_detection_agent(state: ClaimState) -> dict:
    amount = state.get('claim_amount', 0)
    extracted = state.get('extracted_fields', {})

    #placeholder incdicators; replace with real checks later.
    indicators = extracted.get('suspicious_indicators', [])

    high_value = amount > 500_000
    requires_review = high_value or bool(indicators)

    if indicators:
        risk_level = 'high'
    elif high_value:
        risk_level = "medium"
    else :
        risk_level = 'low'

    return {
        'fraud_result': {
            "risk_level": risk_level,
            "indicators": indicators,
            "requires_review": requires_review,
        }
    }

# Claim Summary Agent
def claim_summary_agent(state: ClaimState) -> dict:
    docs = state.get('document_result', {})
    eligibility = state.get('eligibility_result', {})
    fraud = state.get('fraud_results', {})

    reasons = []

    if docs.get('missing_documents'):
        reasons.append(
            "Missing documents: " + ", ".join(docs['missing_documents'])
        )

    reasons.extend(docs.get('issues', []))
    reasons.extend(eligibility.get("issues", []))

    if fraud.get("indicators"):
        reasons.append(
            "Fraud indicators flagged: " 
            + ", ".join(fraud["indicators"])
        )

    if fraud.get("requires_review"):
        reasons.append("Human review is required by risk rules.")

    if not reasons:
        reasons.append("All configured preliminary checks passed.")

    summary = (
        f"Claim ID: {state.get('claim_id', 'N/A')}\n"
        f"Claim amount: {state.get('claim_amount', 0):,.2f}\n"
        f"Document status: {docs.get('status', 'unkown')}\n"
        f"Eligibility status: {eligibility.get('status', 'unknow')}\n"
        f"Fraud risk: {fraud.get('risk_level', 'unkown')}\n"
        f"findings: {'; '.join(reasons)}"
    )

    return {
        "claim_summary" : summary,
        "decision_reasons": reasons,
    }


# Decision Router Node

def decision_router_node(state: ClaimState) -> dict:
    decision = route_claim(state)

    return {
        "decision": decision,
        "review_required": decision == "human_review",
    }

# Human Approval Agent

def human_approval_agent(state: ClaimState) -> dict:
    review = interrupt({
        "message": "This claim requires human review.",
        "claim_id": state.get('claim_id'),
        "claim_summary": state.get('claim_summary'),
        'reasons': state.get("decision_reasons", []),
        "allowed_decisions": [
            "approve",
            "reject",
            "request_information",
        ],
    })

    if not isinstance(review, dict):
        raise ValueError("Reviewer response must be a dictionary.")

    reviewer_decision = review.get('decision')

    if reviewer_decision not in {
        "approve", "reject", 'requerst_information'
    }:
        raise ValueError('Invalid reviewer decision.')

    return {
        "reviewer_decision" : reviewer_decision,
        "reviewer_notes" : str(review.get("notes", "")),
    }

# Final outcome nodes

def approve_claim(state: ClaimState) -> dict:
    return {"final_status": "approved"}

def reject_claim(state: ClaimState) -> dict:
    return {"final_status": "reject"}

def request_information(state: ClaimState) -> dict:
    return {'final_status': "pending_information"}

def finalize_human_review(state: ClaimState) -> dict:
    return {
        "final_status": state["reviewer_decision"]
    }

# Build the langgraph


def build_workflow():
    builder = StateGraph(ClaimState)

    builder.add_node(
        "document_verification",
        document_verification_agent,
    )

    builder.add_node(
        "eligibility_check",
        eligibility_check_agent,
    )

    builder.add_node(
        "fraud_detection",
        fraud_detection_agent,
    )

    builder.add_node(
        "claim_summary",
        claim_summary_agent,
    )

    builder.add_node(
        "decision_router",
        decision_router_node,
    )

    builder.add_node(
        "human_approval",
        human_approval_agent,
    )

    builder.add_node("approve", approve_claim)
    builder.add_node("reject", reject_claim)
    builder.add_node(
        "request_information",
        request_information,
    )
    builder.add_node(
        "finalize_human_review",
        finalize_human_review,
    )


    # Parallel execution: all three check start together.
    builder.add_edge(START, "document_verification")
    builder.add_edge(START, "eligibility_check")
    builder.add_edge(START, 'fraud_detection')

    #Wait for all three checks before continuing.
    builder.add_edge(
        [
            "document_verification",
            "eligibility_check",
            "fraud_detection",
        ],
        "claim_summary",
    )

    builder.add_edge("claim_summary", "decision_router")

    # Conditional routing based on the combined results.
    builder.add_conditional_edges(
        "decision_router",
        lambda state: state['decision'],
        {
            "approve": "approve",
            "reject": "reject",
            "human_review": "human_approval",
            "request_information": "request_information",
        },
    )

    # Human review pauses until a reviewer responds.
    builder.add_edge(
        "human_approval",
        "finalize_human_review",
    )

    builder.add_edge("approve", END)
    builder.add_edge("reject", END)
    builder.add_edge("request_information", END)
    builder.add_edge('finalize_human_review', END)

    #In-memory checkpointing for local development
    checkpointer = InMemorySaver()

    return builder.compile(checkpointer=checkpointer)

graph = build_workflow()
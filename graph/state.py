from typing import Any, TypedDict

class ClaimState(TypedDict, total=False):
    """Shared state for the insurance claim workflow."""
    # Claim information
    claim_id: str
    claimant_name: str
    policy_number: str
    claim_type: str
    claim_amount: float
    incident_date: str

    # Policy information
    policy_start_date: str
    policy_end_date: str
    coverage_limit: float
    policy_active: bool
    coverage_available: bool

    # uploaded documents and extracted information
    documents: list[dict[str, Any]]
    required_documents: list[str]
    provided_documents: list[str]
    extracted_fields: dict[str, Any]

    # Results from parallel agents
    document_result: dict[str, Any]
    eligibility_result: dict[str, Any]
    fraud_results: dict[str, Any]

    #Summary and routing
    claim_summary: str
    decision: str
    decision_reasons: list[str]
    review_required: bool

    # Human review
    reviewer_decision: str
    reviewer_notes: str

    # Final result
    final_status: str
    

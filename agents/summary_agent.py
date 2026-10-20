
from graph.state import ClaimState


def claim_summary_agent(state: ClaimState) -> dict:
    """Summarize claim verification and eligibility findings."""

    documents = state.get("document_result", {})
    eligibility = state.get("eligibility_result", {})
    fraud = state.get("fraud_result", {})

    findings = []

    missing = documents.get("missing_documents", [])
    if missing:
        findings.append(
            "Missing documents: " + ", ".join(missing)
        )

    findings.extend(documents.get("issues", []))
    findings.extend(eligibility.get("issues", []))

    indicators = fraud.get("indicators", [])
    if indicators:
        findings.append(
            "Risk indicators: " + "; ".join(indicators)
        )

    if not findings:
        findings.append(
            "No issues were identified by the configured checks."
        )

    summary = "\n".join([
        f"Claim ID: {state.get('claim_id', 'N/A')}",
        f"Claim type: {state.get('claim_type', 'N/A')}",
        f"Claim amount: {state.get('claim_amount', 0):,.2f}",
        f"Document status: {documents.get('status', 'unknown')}",
        f"Eligibility status: {eligibility.get('status', 'unknown')}",
        f"Fraud risk level: {fraud.get('risk_level', 'unknown')}",
        "Findings:",
        *[f"- {finding}" for finding in findings],
    ])

    return {
        "claim_summary": summary,
        "decision_reasons": findings,
    }

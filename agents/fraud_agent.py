
from graph.state import ClaimState


HIGH_VALUE_THRESHOLD = 500_000


def fraud_detection_agent(state: ClaimState) -> dict:
    """Flag suspicious indicators for further investigation."""

    amount = state.get("claim_amount", 0)
    extracted_fields = state.get("extracted_fields", {})

    indicators = list(
        extracted_fields.get("suspicious_indicators", [])
    )

    if amount > HIGH_VALUE_THRESHOLD:
        indicators.append(
            f"Claim exceeds the configured threshold of "
            f"{HIGH_VALUE_THRESHOLD:,.0f}."
        )

    if indicators:
        risk_level = "high"
        requires_review = True
    else:
        risk_level = "low"
        requires_review = False

    return {
        "fraud_result": {
            "risk_level": risk_level,
            "indicators": indicators,
            "requires_review": requires_review,
        }
    }

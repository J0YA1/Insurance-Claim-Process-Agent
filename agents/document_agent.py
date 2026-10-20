
from graph.state import ClaimState


def document_verification_agent(state: ClaimState) -> dict:
    """Verify the presence of required claim documents."""

    required = state.get("required_documents", [])
    provided = state.get("provided_documents", [])

    required_set = set(required)
    provided_set = set(provided)

    missing = sorted(required_set - provided_set)

    if missing:
        status = "missing"
    else:
        status = "verified"

    return {
        "document_result": {
            "status": status,
            "required_documents": sorted(required_set),
            "provided_documents": sorted(provided_set),
            "missing_documents": missing,
            "issues": (
                [f"Missing document: {name}" for name in missing]
            ),
        }
    }

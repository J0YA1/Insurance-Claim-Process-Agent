
import uuid
import streamlit as st
from langgraph.types import Command
from graph.workflow import graph


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------
st.set_page_config(
    page_title="Insurance Claim Processing Agent",
    page_icon="📋",
    layout="wide"
)

st.title("Insurance Claim Processing Agent")
st.write(
    "Submit an insurance claim for document verification, "
    "eligibility checks, fraud-risk screening, and decision review."
)


# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------
if "workflow_result" not in st.session_state:
    st.session_state.workflow_result = None

if "active_thread_id" not in st.session_state:
    st.session_state.active_thread_id = None

if "pending_review" not in st.session_state:
    st.session_state.pending_review = False


# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------
def display_result(result):
    """Display the results returned by the workflow."""

    st.subheader("Claim Processing Results")

    summary = result.get("claim_summary", "")
    if summary:
        st.markdown("### Claim Summary")
        st.text(summary)

    document_result = result.get("document_result", {})
    eligibility_result = result.get("eligibility_result", {})
    fraud_result = result.get("fraud_result", {})

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("#### Document Verification")
        st.write(
            document_result.get("status", "Not available").replace(
                "_", " "
            ).title()
        )
        missing = document_result.get("missing_documents", [])
        if missing:
            st.warning("Missing: " + ", ".join(missing))

    with col2:
        st.markdown("#### Eligibility")
        st.write(
            eligibility_result.get("status", "Not available").title()
        )
        issues = eligibility_result.get("issues", [])
        for issue in issues:
            st.write(f"- {issue}")

    with col3:
        st.markdown("#### Fraud Risk Screening")
        risk = fraud_result.get("risk_level", "Not available")
        st.write(str(risk).replace("_", " ").title())

        indicators = fraud_result.get("indicators", [])
        for indicator in indicators:
            st.write(f"- {indicator}")

    st.divider()

    # Show the final decision when the workflow has completed.
    final_status = result.get("final_status")
    if final_status:
        st.subheader("Final Decision")
        st.success(str(final_status).replace("_", " ").title())
    elif result.get("__interrupt__"):
        st.warning("The claim is awaiting human review.")
    else:
        st.info("The workflow returned no final status.")

    reasons = result.get("decision_reasons", [])
    if reasons:
        with st.expander("Decision Reasons"):
            for reason in reasons:
                st.write(f"- {reason}")


# --------------------------------------------------
# CLAIM SUBMISSION FORM
# --------------------------------------------------
with st.form("claim_submission_form"):

    st.subheader("1. Claimant and Policy Details")

    col1, col2 = st.columns(2)

    with col1:
        claim_id = st.text_input(
            "Claim ID",
            value=f"CLM-{uuid.uuid4().hex[:8].upper()}"
        )

        claimant_name = st.text_input("Claimant Name")
        policy_number = st.text_input("Policy Number")

        claim_type = st.selectbox(
            "Claim Type",
            ["Health", "Vehicle", "Property", "Travel", "Other"]
        )

    with col2:
        claim_amount = st.number_input(
            "Claim Amount (₹)",
            min_value=0.0,
            value=50000.0,
            step=1000.0
        )

        coverage_limit = st.number_input(
            "Policy Coverage Limit (₹)",
            min_value=0.0,
            value=100000.0,
            step=1000.0
        )

        coverage_available = st.checkbox(
            "The policy covers this type of claim",
            value=True
        )

        incident_date = st.date_input(
            "Incident Date"
        )

    st.subheader("2. Policy Period")

    col1, col2 = st.columns(2)

    with col1:
        policy_start_date = st.date_input(
            "Policy Start Date",
            value=__import__("datetime").date(2026, 1, 1)
        )

    with col2:
        policy_end_date = st.date_input(
            "Policy End Date",
            value=__import__("datetime").date(2026, 12, 31)
        )

    st.subheader("3. Document Verification")

    required_documents = [
        "Claim Form",
        "Policy Document",
        "Medical Bill",
        "Identity Proof",
        "Incident Report"
    ]

    provided_documents = st.multiselect(
        "Select the documents received",
        options=required_documents,
        default=[
            "Claim Form",
            "Policy Document",
            "Medical Bill"
        ],
        help="This version checks document names, not file contents."
    )

    st.subheader("4. Fraud-Risk Screening")

    suspicious_text = st.text_area(
        "Suspicious indicators, if any",
        placeholder=(
            "Enter one indicator per line, or leave blank.\n"
            "Example: Conflicting incident dates"
        )
    )

    submitted = st.form_submit_button(
        "Process Insurance Claim",
        type="primary",
        use_container_width=True
    )


# --------------------------------------------------
# RUN THE LANGGRAPH WORKFLOW
# --------------------------------------------------
if submitted:

    if not claim_id.strip() or not claimant_name.strip():
        st.error("Please enter the Claim ID and Claimant Name.")

    elif not policy_number.strip():
        st.error("Please enter the Policy Number.")

    elif claim_amount <= 0 or coverage_limit <= 0:
        st.error("Claim amount and coverage limit must be greater than zero.")

    elif policy_start_date > policy_end_date:
        st.error("Policy start date cannot be after its end date.")

    else:
        claim_data = {
            "claim_id": claim_id.strip(),
            "claimant_name": claimant_name.strip(),
            "policy_number": policy_number.strip(),
            "claim_type": claim_type,
            "claim_amount": float(claim_amount),
            "incident_date": incident_date.isoformat(),
            "policy_start_date": policy_start_date.isoformat(),
            "policy_end_date": policy_end_date.isoformat(),
            "coverage_limit": float(coverage_limit),
            "coverage_available": coverage_available,
            "required_documents": required_documents,
            "provided_documents": provided_documents,
            "extracted_fields": {
                "suspicious_indicators": [
                    item.strip()
                    for item in suspicious_text.splitlines()
                    if item.strip()
                ]
            }
        }

        thread_id = str(uuid.uuid4())
        config = {
            "configurable": {
                "thread_id": thread_id
            }
        }

        try:
            with st.spinner("Processing the insurance claim..."):
                result = graph.invoke(claim_data, config=config)

            st.session_state.active_thread_id = thread_id
            st.session_state.workflow_result = result
            st.session_state.pending_review = bool(
                result.get("__interrupt__")
            )

            st.rerun()

        except Exception as error:
            st.error(
                f"Workflow execution failed: "
                f"{type(error).__name__}: {error}"
            )


# --------------------------------------------------
# HUMAN REVIEW
# --------------------------------------------------
result = st.session_state.workflow_result

if result is not None:

    if st.session_state.pending_review:

        st.divider()
        st.subheader("5. Human Review Required")

        st.warning(
            "The workflow paused for a human decision. "
            "Review the claim findings before continuing."
        )

        for interrupt_item in result.get("__interrupt__", []):
            review_data = interrupt_item.value
            st.json(review_data)

        with st.form("human_review_form"):

            reviewer_decision = st.selectbox(
                "Review Decision",
                [
                    "request_information",
                    "approve",
                    "reject"
                ],
                format_func=lambda value: value.replace(
                    "_", " "
                ).title()
            )

            reviewer_notes = st.text_area(
                "Reviewer Notes",
                placeholder="Explain the reason for your decision."
            )

            review_submitted = st.form_submit_button(
                "Submit Review",
                type="primary",
                use_container_width=True
            )

        if review_submitted:

            try:
                config = {
                    "configurable": {
                        "thread_id": st.session_state.active_thread_id
                    }
                }

                review_response = {
                    "decision": reviewer_decision,
                    "notes": reviewer_notes
                }

                with st.spinner("Resuming workflow..."):
                    updated_result = graph.invoke(
                        Command(resume=review_response),
                        config=config
                    )

                st.session_state.workflow_result = updated_result
                st.session_state.pending_review = bool(
                    updated_result.get("__interrupt__")
                )

                st.rerun()

            except Exception as error:
                st.error(
                    f"Could not submit the review: "
                    f"{type(error).__name__}: {error}"
                )

    else:
        display_result(result)

    if st.button("Clear Results"):
        st.session_state.workflow_result = None
        st.session_state.active_thread_id = None
        st.session_state.pending_review = False
        st.rerun()

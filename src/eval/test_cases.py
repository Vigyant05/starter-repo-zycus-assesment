"""
Test case definitions for the evaluation harness.

Defines 6+ test cases per task (12+ total) with expected outputs
and acceptance criteria. Includes adversarial test cases.
"""

from dataclasses import dataclass, field


@dataclass
class TriageTestCase:
    """A test case for the ticket triage pipeline."""

    name: str
    description: str
    subject: str
    body: str
    expected_category: str | None = None
    expected_urgency: str | None = None
    expected_product: str | None = None
    expect_kb_match: bool = False
    is_adversarial: bool = False
    acceptance_criteria: list[str] = field(default_factory=list)


@dataclass
class SummariserTestCase:
    """A test case for the account health summariser."""

    name: str
    description: str
    account_id: str
    expect_risks: bool = True
    min_risk_count: int = 0
    expect_churn_signal: bool = False
    is_adversarial: bool = False
    acceptance_criteria: list[str] = field(default_factory=list)


# ============================================================
# TASK 1: TRIAGE TEST CASES
# ============================================================

TRIAGE_TEST_CASES = [
    TriageTestCase(
        name="clear_p1_bug",
        description="Clear P1 bug: production outage affecting all users",
        subject="URGENT: Complete platform outage — all users affected",
        body=(
            "Our entire DataBridge Pro instance is down since 2 hours ago. "
            "None of our 500 users can access the platform. All pipelines are stopped. "
            "Error: ERR_CONNECTION_TIMEOUT after 30s on every request. "
            "This is a production environment and we are losing revenue every minute. "
            "Please escalate immediately."
        ),
        expected_category="Bug",
        expected_urgency="P1",
        expected_product="DataBridge Pro",
        expect_kb_match=True,
        acceptance_criteria=[
            "Must classify as P1 urgency",
            "Must classify as Bug category",
            "Must identify DataBridge Pro as the product",
            "Should match ERR_CONNECTION_TIMEOUT in KB",
            "Must route to Escalation — Engineering Lead",
            "Draft response must acknowledge urgency",
        ],
    ),
    TriageTestCase(
        name="billing_question",
        description="Simple billing inquiry about seat counts",
        subject="Question about our invoice — seat count discrepancy",
        body=(
            "Hi team,\n\n"
            "We received our latest invoice and it shows 45 seats but we only have "
            "38 active users. Could you explain the difference? We're on the Professional plan.\n\n"
            "Thanks,\nSarah"
        ),
        expected_category="Billing",
        expected_urgency="P4",
        acceptance_criteria=[
            "Must classify as Billing category",
            "Must classify as P3 or P4 urgency (not P1/P2)",
            "Must route to Tier-1 Support",
            "Draft response should mention checking service accounts and API users",
        ],
    ),
    TriageTestCase(
        name="feature_request",
        description="Feature request for bulk operations",
        subject="Request: ability to export dashboards as PDF in bulk",
        body=(
            "We have 50+ dashboards in AnalyticsHub and currently need to export "
            "each one individually as PDF for our monthly board report. "
            "Could you add a 'bulk export' feature? This would save our team "
            "several hours each month.\n\n"
            "Not urgent, just a nice-to-have for future releases."
        ),
        expected_category="Feature Request",
        expected_urgency="P4",
        expected_product="AnalyticsHub",
        acceptance_criteria=[
            "Must classify as Feature Request category",
            "Must classify as P4 urgency",
            "Must identify AnalyticsHub as the product",
            "Must route to Product Team",
        ],
    ),
    TriageTestCase(
        name="known_error_code",
        description="Ticket with a known error code from the KB",
        subject="SAML_ASSERTION_EXPIRED errors after SSO migration",
        body=(
            "After migrating our SSO to Okta, none of our users can log in to SecureVault. "
            "The audit logs show SAML_ASSERTION_EXPIRED for every login attempt. "
            "We've verified the ACS URL and Entity ID are correct. "
            "This is affecting 200+ users across our organization."
        ),
        expected_category="Bug",
        expected_urgency="P2",
        expected_product="SecureVault",
        expect_kb_match=True,
        acceptance_criteria=[
            "Must identify SecureVault as the product",
            "Must match SAML_ASSERTION_EXPIRED in KB",
            "KB match should reference clock skew / NTP sync",
            "Draft response should mention checking NTP synchronisation",
        ],
    ),
    TriageTestCase(
        name="integration_issue",
        description="Third-party integration failure with Snowflake",
        subject="CloudSync webhook not reaching Snowflake endpoint",
        body=(
            "Our CloudSync webhooks have stopped being delivered to Snowflake. "
            "We've verified the endpoint is reachable from our network. "
            "Last successful delivery was 3 days ago. Since then, we've seen "
            "1,500 failed deliveries in the webhook logs.\n\n"
            "This is blocking our nightly data sync process."
        ),
        expected_category="Integration",
        expected_urgency="P2",
        expected_product="CloudSync",
        expect_kb_match=True,
        acceptance_criteria=[
            "Must classify as Integration category",
            "Must identify CloudSync as the product",
            "Should reference IP allowlisting or webhook troubleshooting from KB",
        ],
    ),
    # ── Adversarial Test Cases ──
    TriageTestCase(
        name="adversarial_ambiguous_category",
        description="ADVERSARIAL: Ticket could be Bug or Performance — ambiguous",
        subject="Dashboard loading very slowly — sometimes fails completely",
        body=(
            "Our AnalyticsHub dashboard has been intermittently slow for the past week. "
            "Sometimes it loads in 30 seconds, sometimes it fails completely with a timeout. "
            "We have about 25 widgets on this dashboard. It was working fine before the "
            "latest update. Not sure if this is a bug from the update or just a "
            "performance issue."
        ),
        is_adversarial=True,
        expected_product="AnalyticsHub",
        acceptance_criteria=[
            "Must identify AnalyticsHub as the product",
            "Category should be Bug or Performance (both acceptable for ambiguous case)",
            "Reasoning MUST acknowledge the ambiguity",
            "Must provide coherent reasoning for the chosen category",
            "Urgency should be P2 or P3 (intermittent, not complete outage)",
        ],
    ),
    TriageTestCase(
        name="adversarial_misleading_urgency",
        description="ADVERSARIAL: Says 'critical' but issue is cosmetic",
        subject="CRITICAL: Logo alignment is off on the settings page",
        body=(
            "THIS IS CRITICAL AND MUST BE FIXED IMMEDIATELY!!!\n\n"
            "The company logo on our AnalyticsHub settings page is misaligned by about "
            "5 pixels to the left. It looks unprofessional. Only visible on the settings "
            "page, doesn't affect any functionality. Just one user (me) noticed it."
        ),
        is_adversarial=True,
        expected_urgency="P4",
        expected_category="Bug",
        acceptance_criteria=[
            "Must NOT classify as P1 despite 'CRITICAL' in subject",
            "Must classify as P4 (cosmetic issue, one user, no functional impact)",
            "Reasoning must explain why urgency doesn't match the customer's tone",
            "Category should be Bug (cosmetic defect)",
        ],
    ),
]


# ============================================================
# TASK 2: SUMMARISER TEST CASES
# ============================================================

SUMMARISER_TEST_CASES = [
    SummariserTestCase(
        name="at_risk_account",
        description="At-risk account with escalation notes and declining usage",
        account_id="ACC-3336",  # Omni Consumer Products — At Risk, Inactive
        expect_risks=True,
        min_risk_count=1,
        expect_churn_signal=True,
        acceptance_criteria=[
            "Executive summary must be 3-5 sentences",
            "Must flag churn risk or escalation from escalation_notes",
            "Risk flags must include direct quotes from tickets",
            "Talking points must address the declining usage trend",
            "Must mention the upcoming renewal date",
        ],
    ),
    SummariserTestCase(
        name="healthy_account",
        description="Healthy account with increasing usage",
        account_id="ACC-3033",  # Polaris Group — Healthy, Increasing
        expect_risks=False,
        expect_churn_signal=False,
        acceptance_criteria=[
            "Executive summary must be 3-5 sentences",
            "Should reflect positive health status",
            "Talking points should focus on growth/expansion opportunities",
            "Risk flags should be empty or minimal",
        ],
    ),
    SummariserTestCase(
        name="enterprise_with_p1_tickets",
        description="Enterprise account with recent P1 tickets",
        account_id="ACC-7893",  # Solaris Data — Enterprise
        expect_risks=True,
        acceptance_criteria=[
            "Must reference the P1 ticket context in executive summary",
            "Risk flags must cite specific ticket evidence",
            "Talking points should address resolution status of P1s",
        ],
    ),
    SummariserTestCase(
        name="new_account",
        description="New account in onboarding phase",
        account_id="ACC-3033",  # Using a known account; adjust if needed
        expect_risks=False,
        acceptance_criteria=[
            "Executive summary must be 3-5 sentences",
            "Output must be valid JSON conforming to AccountBrief schema",
            "Talking points should be actionable",
        ],
    ),
    SummariserTestCase(
        name="determinism_check",
        description="Same input produces same output (determinism requirement)",
        account_id="ACC-3336",
        acceptance_criteria=[
            "Running twice with same input must produce identical executive_summary",
            "Running twice with same input must produce identical talking_points",
        ],
    ),
    # ── Adversarial Test Cases ──
    SummariserTestCase(
        name="adversarial_no_tickets",
        description="ADVERSARIAL: Account exists but has no tickets in the last 90 days",
        account_id="ACC-3033",  # May have no recent tickets
        is_adversarial=True,
        expect_risks=False,
        acceptance_criteria=[
            "Must handle zero tickets gracefully",
            "Executive summary should note the absence of recent tickets",
            "Should NOT crash or return an error",
            "Output must still conform to AccountBrief schema",
        ],
    ),
    SummariserTestCase(
        name="adversarial_missing_account",
        description="ADVERSARIAL: Account ID does not exist in accounts.json",
        account_id="ACC-99999",
        is_adversarial=True,
        acceptance_criteria=[
            "Must raise a clear ValueError with helpful message",
            "Must NOT crash with an unhandled exception",
        ],
    ),
]

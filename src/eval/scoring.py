"""
Scoring functions for the evaluation harness.

Combines rule-based checks (schema validation, enum correctness, determinism)
with LLM-as-judge quality scoring (0-1 scale).
"""

import json
from dataclasses import dataclass, field

from groq import Groq

from src.config import GROQ_API_KEY, MODEL_NAME, TEMPERATURE, SEED
from src.triage.schemas import TriageResult, IssueCategory, UrgencyTier
from src.summariser.schemas import AccountBrief


@dataclass
class TestResult:
    """Result of a single test case evaluation."""

    test_name: str
    passed: bool
    quality_score: float  # 0.0 to 1.0
    rule_checks: dict[str, bool] = field(default_factory=dict)
    llm_judge_score: float = 0.0
    llm_judge_reasoning: str = ""
    error: str | None = None
    is_adversarial: bool = False


def _get_client() -> Groq:
    return Groq(api_key=GROQ_API_KEY)


# ── Rule-Based Scoring ─────────────────────────────────────────

def check_triage_rules(
    result: TriageResult,
    expected_category: str | None = None,
    expected_urgency: str | None = None,
    expected_product: str | None = None,
    expect_kb_match: bool = False,
) -> dict[str, bool]:
    """
    Run rule-based checks on a TriageResult.

    Returns a dict of check_name -> pass/fail.
    """
    checks = {}

    # Schema validation (always passes if we got a TriageResult)
    checks["schema_valid"] = True

    # Category enum check
    checks["category_valid_enum"] = result.issue_category.value in [c.value for c in IssueCategory]

    # Urgency enum check
    checks["urgency_valid_enum"] = result.urgency_tier.value in [u.value for u in UrgencyTier]

    # Non-empty required fields
    checks["has_reasoning"] = len(result.reasoning.strip()) > 10
    checks["has_draft_response"] = len(result.draft_response.strip()) > 20
    checks["has_recommended_team"] = len(result.recommended_team.strip()) > 2
    checks["has_product"] = len(result.product.strip()) > 0
    checks["has_product_area"] = len(result.product_area.strip()) > 0

    # Expected value checks (if provided)
    if expected_category:
        checks["expected_category_match"] = result.issue_category.value == expected_category

    if expected_urgency:
        checks["expected_urgency_match"] = result.urgency_tier.value == expected_urgency

    if expected_product:
        checks["expected_product_match"] = result.product == expected_product

    if expect_kb_match:
        checks["kb_match_present"] = result.kb_match is not None

    return checks


def check_summariser_rules(
    result: AccountBrief,
    expect_risks: bool = True,
    min_risk_count: int = 0,
    expect_churn_signal: bool = False,
) -> dict[str, bool]:
    """
    Run rule-based checks on an AccountBrief.

    Returns a dict of check_name -> pass/fail.
    """
    checks = {}

    # Schema validation
    checks["schema_valid"] = True

    # Executive summary length (3-5 sentences)
    sentences = [s.strip() for s in result.executive_summary.split(".") if s.strip()]
    checks["summary_length_ok"] = 2 <= len(sentences) <= 7  # Some tolerance

    # Non-empty fields
    checks["has_executive_summary"] = len(result.executive_summary.strip()) > 30
    checks["has_talking_points"] = len(result.talking_points) > 0

    # Risk expectations
    if expect_risks:
        checks["has_risk_flags"] = len(result.open_risks) > 0

    if min_risk_count > 0:
        checks["min_risk_count_met"] = len(result.open_risks) >= min_risk_count

    # Check that risk flags have quotes (justification)
    if result.open_risks:
        checks["risks_have_quotes"] = all(
            len(r.justification.strip()) > 10 for r in result.open_risks
        )

    if expect_churn_signal:
        churn_types = {"churn_risk", "renewal_risk"}
        checks["churn_signal_found"] = any(
            r.signal_type.value in churn_types for r in result.open_risks
        )

    return checks


# ── LLM-as-Judge Scoring ──────────────────────────────────────

LLM_JUDGE_SYSTEM_PROMPT = """You are a quality evaluator for AI-generated support triage and account brief outputs.

Score the output on a scale of 0.0 to 1.0 based on these criteria:
- Correctness: Is the classification/analysis factually sound?
- Completeness: Are all required elements present and substantive?
- Coherence: Is the reasoning logical and well-explained?
- Professionalism: Is the draft response / talking points appropriate and helpful?
- Evidence-based: Are claims supported by evidence from the input?

Respond with ONLY valid JSON:
{
  "score": <float 0.0-1.0>,
  "reasoning": "<brief explanation of the score>"
}
"""


def llm_judge_triage(
    ticket_subject: str,
    ticket_body: str,
    result: TriageResult,
    acceptance_criteria: list[str],
) -> tuple[float, str]:
    """
    Use an LLM to judge the quality of a triage result.

    Returns (score, reasoning) tuple.
    """
    client = _get_client()

    criteria_text = "\n".join(f"- {c}" for c in acceptance_criteria)

    user_prompt = f"""## Input Ticket
**Subject:** {ticket_subject}
**Body:** {ticket_body}

## Triage Output
{result.model_dump_json(indent=2)}

## Acceptance Criteria
{criteria_text}

Rate the quality of this triage output (0.0-1.0).
"""

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            temperature=0,
            seed=SEED,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": LLM_JUDGE_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )

        data = json.loads(response.choices[0].message.content)
        return float(data.get("score", 0.0)), data.get("reasoning", "")
    except Exception as e:
        return 0.0, f"LLM judge error: {str(e)}"


def llm_judge_summariser(
    account_id: str,
    result: AccountBrief,
    acceptance_criteria: list[str],
) -> tuple[float, str]:
    """
    Use an LLM to judge the quality of an account brief.

    Returns (score, reasoning) tuple.
    """
    client = _get_client()

    criteria_text = "\n".join(f"- {c}" for c in acceptance_criteria)

    user_prompt = f"""## Account Brief Output
{result.model_dump_json(indent=2)}

## Acceptance Criteria
{criteria_text}

Rate the quality of this account brief (0.0-1.0).
"""

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            temperature=0,
            seed=SEED,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": LLM_JUDGE_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )

        data = json.loads(response.choices[0].message.content)
        return float(data.get("score", 0.0)), data.get("reasoning", "")
    except Exception as e:
        return 0.0, f"LLM judge error: {str(e)}"


def compute_quality_score(rule_checks: dict[str, bool], llm_score: float) -> float:
    """
    Compute a combined quality score from rule checks and LLM judge.

    Rule checks contribute 50% (all-or-nothing per check),
    LLM judge contributes 50%.
    """
    if not rule_checks:
        rule_score = 0.0
    else:
        rule_score = sum(1 for v in rule_checks.values() if v) / len(rule_checks)

    return round(rule_score * 0.5 + llm_score * 0.5, 3)

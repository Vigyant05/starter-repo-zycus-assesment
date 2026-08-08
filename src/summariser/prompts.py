"""
Versioned prompt templates for the TAM account health summariser.

Uses a two-step prompt chain:
  Step 1: Extract risk signals from tickets (with direct quotes)
  Step 2: Synthesize the 3-section account brief

Each prompt has a version identifier and changelog for traceability.
"""

from src.triage.prompts import PROMPT_REGISTRY

# ============================================================
# STEP 1: RISK EXTRACTION — v1.1
# ============================================================
RISK_EXTRACTION_VERSION = "v1.1"
RISK_EXTRACTION_CHANGELOG = """
- v1.0 (2026-08-08): Initial risk extraction prompt.
- v1.1 (2026-08-08): Added explicit requirement for direct quotes. Added
  adoption_decline and renewal_risk signal types.
"""

RISK_EXTRACTION_SYSTEM_PROMPT = """You are a customer risk analysis specialist for a SaaS platform.
Your job is to analyze support tickets from a specific customer account and identify
signals that suggest churn risk, escalation, product dissatisfaction, adoption decline,
or renewal risk.

## Risk Signal Types
- churn_risk: Customer expressing intent to leave, evaluating competitors, or threatening cancellation
- escalation: Frustration with support, demanding management involvement, or repeated unresolved issues
- product_dissatisfaction: Complaints about product quality, reliability, or missing critical features
- adoption_decline: Reports of users not using the product, requests to reduce seats, or disengagement
- renewal_risk: Concerns about pricing, contract terms, or uncertainty about renewal

## Rules
1. For EACH flagged risk, you MUST include a direct quote from the ticket body as justification.
2. The quote must be the exact text from the ticket — do not paraphrase.
3. Only flag genuine risk signals. Not every negative ticket is a churn signal.
4. Rate severity as high/medium/low based on the strength of the signal and business impact.
5. Include a concrete recommendation for the TAM for each flag.

Respond with a JSON array of risk flags. If no risks are found, return an empty array.
"""

RISK_EXTRACTION_USER_TEMPLATE = """## Account: {company} ({account_id})

**Account Context:**
- Plan: {plan_tier}
- ARR: ${arr_usd:,}
- Health Status: {health_status}
- Usage Trend: {usage_trend}
- Seats: {seats_active}/{seats_licensed} active
- Open Tickets: {open_tickets}
- P1 Tickets (last 30d): {p1_tickets_last_30d}
- Renewal Date: {renewal_date}
- Last QBR: {last_qbr_date}
- NPS Score: {nps_score}

**Escalation Notes from Account Record:**
{escalation_notes}

---

## Recent Support Tickets (last {days} days)

{tickets_text}

---

Analyze these tickets for risk signals. For each risk found, provide:
- ticket_id
- signal_type (churn_risk, escalation, product_dissatisfaction, adoption_decline, renewal_risk)
- severity (high, medium, low)
- justification (EXACT direct quote from the ticket body)
- recommendation (concrete action for the TAM)
"""

PROMPT_REGISTRY["risk_extraction_system"] = {
    "version": RISK_EXTRACTION_VERSION,
    "changelog": RISK_EXTRACTION_CHANGELOG,
    "template": RISK_EXTRACTION_SYSTEM_PROMPT,
}

PROMPT_REGISTRY["risk_extraction_user"] = {
    "version": RISK_EXTRACTION_VERSION,
    "changelog": RISK_EXTRACTION_CHANGELOG,
    "template": RISK_EXTRACTION_USER_TEMPLATE,
}

# ============================================================
# STEP 2: BRIEF SYNTHESIS — v1.1
# ============================================================
BRIEF_SYNTHESIS_VERSION = "v1.1"
BRIEF_SYNTHESIS_CHANGELOG = """
- v1.0 (2026-08-08): Initial brief synthesis prompt.
- v1.1 (2026-08-08): Added instruction to keep executive summary to exactly 3-5
  sentences. Added instruction to prioritise talking points by urgency.
"""

BRIEF_SYNTHESIS_SYSTEM_PROMPT = """You are a TAM briefing assistant that creates concise, actionable
account health briefs for Technical Account Managers preparing for Quarterly Business Reviews (QBRs).

## Output Format
Produce a JSON object with these fields:
- executive_summary: Exactly 3-5 sentences covering overall account health, key concerns, and outlook.
- talking_points: List of 3-7 recommended talking points for the TAM, ordered by priority.

## Rules
1. The executive summary should be data-driven. Reference specific metrics (ARR, seat usage, ticket counts).
2. Talking points should be actionable and specific — not generic advice.
3. If there are identified risk flags, incorporate them into the summary and talking points.
4. Be objective and balanced — mention positives as well as concerns.
5. Keep the tone professional but direct. TAMs need clarity, not fluff.

Respond ONLY with valid JSON.
"""

BRIEF_SYNTHESIS_USER_TEMPLATE = """## Account: {company} ({account_id})

**Account Data:**
- Plan: {plan_tier} | ARR: ${arr_usd:,}
- Health: {health_status} | Usage Trend: {usage_trend}
- Seats: {seats_active}/{seats_licensed} active ({seat_utilization}% utilization)
- Products: {products}
- Renewal: {renewal_date} | Last QBR: {last_qbr_date}
- TAM: {tam} | Region: {region} | Industry: {industry}
- NPS: {nps_score} | Last Login: {last_login_days_ago} days ago
- Integrations: {integrations}

**Recent Ticket Summary ({days} days):**
- Total tickets: {total_tickets}
- By urgency: {urgency_breakdown}
- By category: {category_breakdown}
- By status: {status_breakdown}

**Identified Risk Flags:**
{risk_flags_text}

---

Generate the executive_summary and talking_points for this account brief.
"""

PROMPT_REGISTRY["brief_synthesis_system"] = {
    "version": BRIEF_SYNTHESIS_VERSION,
    "changelog": BRIEF_SYNTHESIS_CHANGELOG,
    "template": BRIEF_SYNTHESIS_SYSTEM_PROMPT,
}

PROMPT_REGISTRY["brief_synthesis_user"] = {
    "version": BRIEF_SYNTHESIS_VERSION,
    "changelog": BRIEF_SYNTHESIS_CHANGELOG,
    "template": BRIEF_SYNTHESIS_USER_TEMPLATE,
}


def format_risk_extraction_prompt(
    account: dict,
    tickets: list[dict],
    days: int = 90,
) -> str:
    """Format the risk extraction user prompt with account and ticket data."""
    # Format tickets into readable text
    tickets_text = ""
    if tickets:
        ticket_sections = []
        for t in tickets:
            ticket_sections.append(
                f"### {t['ticket_id']} — {t['subject']}\n"
                f"**Product:** {t['product']} | **Category:** {t['category']} | "
                f"**Urgency:** {t['urgency']} | **Status:** {t['status']}\n"
                f"**Created:** {t['created_at']}\n\n"
                f"{t['body']}"
            )
        tickets_text = "\n\n---\n\n".join(ticket_sections)
    else:
        tickets_text = "No tickets found in this period."

    # Format escalation notes
    escalation_notes = "\n".join(
        f"- {note}" for note in account.get("escalation_notes", [])
    )
    if not escalation_notes:
        escalation_notes = "None recorded."

    return RISK_EXTRACTION_USER_TEMPLATE.format(
        company=account["company"],
        account_id=account["account_id"],
        plan_tier=account["plan_tier"],
        arr_usd=account["arr_usd"],
        health_status=account["health_status"],
        usage_trend=account["usage_trend"],
        seats_active=account["seats_active"],
        seats_licensed=account["seats_licensed"],
        open_tickets=account["open_tickets"],
        p1_tickets_last_30d=account["p1_tickets_last_30d"],
        renewal_date=account["renewal_date"],
        last_qbr_date=account["last_qbr_date"],
        nps_score=account.get("nps_score") or "Not provided",
        escalation_notes=escalation_notes,
        days=days,
        tickets_text=tickets_text,
    )


def format_brief_synthesis_prompt(
    account: dict,
    tickets: list[dict],
    risk_flags_text: str,
    days: int = 90,
) -> str:
    """Format the brief synthesis user prompt with account data and risk flags."""
    from collections import Counter

    # Compute ticket breakdowns
    urgency_counts = Counter(t["urgency"] for t in tickets)
    category_counts = Counter(t["category"] for t in tickets)
    status_counts = Counter(t["status"] for t in tickets)

    urgency_breakdown = ", ".join(f"{k}: {v}" for k, v in sorted(urgency_counts.items()))
    category_breakdown = ", ".join(f"{k}: {v}" for k, v in sorted(category_counts.items()))
    status_breakdown = ", ".join(f"{k}: {v}" for k, v in sorted(status_counts.items()))

    seat_utilization = round(account["seats_active"] / account["seats_licensed"] * 100) if account["seats_licensed"] else 0

    return BRIEF_SYNTHESIS_USER_TEMPLATE.format(
        company=account["company"],
        account_id=account["account_id"],
        plan_tier=account["plan_tier"],
        arr_usd=account["arr_usd"],
        health_status=account["health_status"],
        usage_trend=account["usage_trend"],
        seats_active=account["seats_active"],
        seats_licensed=account["seats_licensed"],
        seat_utilization=seat_utilization,
        products=", ".join(account["products"]),
        renewal_date=account["renewal_date"],
        last_qbr_date=account["last_qbr_date"],
        tam=account["tam"],
        region=account["region"],
        industry=account["industry"],
        nps_score=account.get("nps_score") or "Not provided",
        last_login_days_ago=account.get("last_login_days_ago", "Unknown"),
        integrations=", ".join(account.get("integrations_active", [])) or "None",
        total_tickets=len(tickets),
        urgency_breakdown=urgency_breakdown or "None",
        category_breakdown=category_breakdown or "None",
        status_breakdown=status_breakdown or "None",
        risk_flags_text=risk_flags_text or "No risk signals identified.",
        days=days,
    )

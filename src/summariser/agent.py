"""
Core TAM account health summariser agent.

Uses a two-step prompt chain:
  1. Analyse tickets for risk signals (with direct quotes)
  2. Synthesise a 3-section account brief

Deterministic output via temperature=0 and seed parameter.
"""

import json
from typing import AsyncGenerator

from groq import Groq

from src.config import (
    GROQ_API_KEY,
    MODEL_NAME,
    TEMPERATURE,
    SEED,
    get_account_map,
    get_account_tickets,
)
from src.summariser.schemas import AccountBrief, RiskFlag
from src.summariser.prompts import (
    RISK_EXTRACTION_SYSTEM_PROMPT,
    BRIEF_SYNTHESIS_SYSTEM_PROMPT,
    format_risk_extraction_prompt,
    format_brief_synthesis_prompt,
)


def _get_client() -> Groq:
    """Get a Groq client instance."""
    return Groq(api_key=GROQ_API_KEY)


def _parse_json_response(content: str) -> dict | list:
    """Parse JSON from LLM response, handling markdown code fences."""
    text = content.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return json.loads(text)


def _extract_risks(
    client: Groq,
    account: dict,
    tickets: list[dict],
    days: int = 90,
) -> list[RiskFlag]:
    """
    Step 1: Extract risk signals from ticket history.

    Returns a list of validated RiskFlag objects.
    """
    user_prompt = format_risk_extraction_prompt(account, tickets, days)

    response = client.chat.completions.create(
        model=MODEL_NAME,
        temperature=TEMPERATURE,
        seed=SEED,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": RISK_EXTRACTION_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": user_prompt
                + "\n\nRespond with a JSON object containing a 'risk_flags' array.",
            },
        ],
    )

    raw = _parse_json_response(response.choices[0].message.content)

    # Handle both direct array and wrapped object
    if isinstance(raw, list):
        flags_data = raw
    elif isinstance(raw, dict):
        flags_data = raw.get("risk_flags", raw.get("risks", []))
    else:
        flags_data = []

    # Validate each flag
    risk_flags = []
    for flag_data in flags_data:
        try:
            risk_flags.append(RiskFlag.model_validate(flag_data))
        except Exception:
            continue  # Skip malformed flags

    # Sort deterministically: by severity (high first), then ticket_id
    severity_order = {"high": 0, "medium": 1, "low": 2}
    risk_flags.sort(
        key=lambda f: (severity_order.get(f.severity.value, 3), f.ticket_id)
    )

    return risk_flags


def _synthesise_brief(
    client: Groq,
    account: dict,
    tickets: list[dict],
    risk_flags: list[RiskFlag],
    days: int = 90,
) -> dict:
    """
    Step 2: Synthesise the 3-section account brief.

    Returns a dict with executive_summary and talking_points.
    """
    # Format risk flags for the prompt
    if risk_flags:
        risk_text_parts = []
        for f in risk_flags:
            risk_text_parts.append(
                f"- **{f.signal_type.value}** ({f.severity.value}) — "
                f"Ticket {f.ticket_id}: \"{f.justification}\" → {f.recommendation}"
            )
        risk_flags_text = "\n".join(risk_text_parts)
    else:
        risk_flags_text = ""

    user_prompt = format_brief_synthesis_prompt(
        account, tickets, risk_flags_text, days
    )

    response = client.chat.completions.create(
        model=MODEL_NAME,
        temperature=TEMPERATURE,
        seed=SEED,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": BRIEF_SYNTHESIS_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )

    return _parse_json_response(response.choices[0].message.content)


def generate_account_brief(account_id: str, days: int = 90) -> AccountBrief:
    """
    Generate a complete account health brief.

    Args:
        account_id: The account ID to generate a brief for.
        days: Number of days of ticket history to consider.

    Returns:
        AccountBrief with executive summary, risk flags, and talking points.

    Raises:
        ValueError: If the account_id is not found.
    """
    # Load account
    account_map = get_account_map()
    account = account_map.get(account_id)
    if not account:
        raise ValueError(
            f"Account {account_id} not found in accounts.json. "
            f"Available accounts: {list(account_map.keys())[:5]}..."
        )

    # Load tickets for this account
    tickets = get_account_tickets(account_id, days=days)

    # Step 1: Extract risk signals
    client = _get_client()
    risk_flags = _extract_risks(client, account, tickets, days)

    # Step 2: Synthesise the brief
    brief_data = _synthesise_brief(client, account, tickets, risk_flags, days)

    # Build the final AccountBrief
    return AccountBrief(
        account_id=account_id,
        company=account["company"],
        executive_summary=brief_data.get("executive_summary", ""),
        open_risks=risk_flags,
        talking_points=brief_data.get("talking_points", []),
        health_status=account["health_status"],
        arr_usd=account["arr_usd"],
        renewal_date=account["renewal_date"],
        tickets_analysed=len(tickets),
    )


async def generate_account_brief_stream(
    account_id: str, days: int = 90
) -> AsyncGenerator[str, None]:
    """
    Stream the account brief generation (bonus: streaming output).

    Yields status updates and the final brief as it's generated.
    """
    # Load account
    account_map = get_account_map()
    account = account_map.get(account_id)
    if not account:
        yield json.dumps({"error": f"Account {account_id} not found"})
        return

    yield json.dumps({"status": "loading_tickets", "company": account["company"]}) + "\n"

    tickets = get_account_tickets(account_id, days=days)
    yield json.dumps({"status": "tickets_loaded", "count": len(tickets)}) + "\n"

    # Step 1: Extract risks (streaming)
    yield json.dumps({"status": "extracting_risks"}) + "\n"
    client = _get_client()
    risk_flags = _extract_risks(client, account, tickets, days)
    yield json.dumps({
        "status": "risks_extracted",
        "risk_count": len(risk_flags),
        "risks_preview": [f.model_dump() for f in risk_flags[:3]],
    }) + "\n"

    # Step 2: Synthesise brief (streaming)
    yield json.dumps({"status": "synthesising_brief"}) + "\n"

    # Stream the synthesis LLM call
    if risk_flags:
        risk_text_parts = []
        for f in risk_flags:
            risk_text_parts.append(
                f"- **{f.signal_type.value}** ({f.severity.value}) — "
                f"Ticket {f.ticket_id}: \"{f.justification}\" → {f.recommendation}"
            )
        risk_flags_text = "\n".join(risk_text_parts)
    else:
        risk_flags_text = ""

    user_prompt = format_brief_synthesis_prompt(
        account, tickets, risk_flags_text, days
    )

    stream = client.chat.completions.create(
        model=MODEL_NAME,
        temperature=TEMPERATURE,
        seed=SEED,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": BRIEF_SYNTHESIS_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        stream=True,
    )

    full_content = ""
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            token = chunk.choices[0].delta.content
            full_content += token
            yield token

    # Final: yield the complete validated brief
    try:
        brief_data = _parse_json_response(full_content)
        brief = AccountBrief(
            account_id=account_id,
            company=account["company"],
            executive_summary=brief_data.get("executive_summary", ""),
            open_risks=risk_flags,
            talking_points=brief_data.get("talking_points", []),
            health_status=account["health_status"],
            arr_usd=account["arr_usd"],
            renewal_date=account["renewal_date"],
            tickets_analysed=len(tickets),
        )
        yield "\n\n---VALIDATED---\n" + brief.model_dump_json(indent=2)
    except Exception as e:
        yield f"\n\n---VALIDATION_ERROR---\n{str(e)}"

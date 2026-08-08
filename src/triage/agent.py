"""
Core ticket triage agent.

Accepts a raw support ticket, retrieves relevant knowledge-base context
via RAG, and uses an LLM to produce a structured triage output.
"""

import json
from typing import AsyncGenerator

from groq import Groq

from src.config import GROQ_API_KEY, MODEL_NAME, TEMPERATURE, SEED
from src.rag.retriever import retrieve_for_ticket, RetrievalResult
from src.triage.schemas import TriageResult, TicketInput
from src.triage.prompts import TRIAGE_SYSTEM_PROMPT, format_triage_user_prompt


def _format_kb_context(results: list[RetrievalResult]) -> str:
    """Format retrieval results into a context string for the prompt."""
    if not results:
        return ""

    sections = []
    for i, r in enumerate(results, 1):
        sections.append(
            f"### KB Document {i}: {r.source_file}\n"
            f"**Section:** {r.heading_path}\n"
            f"**Category:** {r.category}\n\n"
            f"{r.text}"
        )
    return "\n\n---\n\n".join(sections)


def _get_client() -> Groq:
    """Get a Groq client instance."""
    return Groq(api_key=GROQ_API_KEY)


def _parse_triage_response(content: str) -> TriageResult:
    """Parse the LLM response into a TriageResult, handling JSON extraction."""
    # Strip markdown code fences if present
    text = content.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last lines (code fences)
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    data = json.loads(text)

    # Handle nested kb_match
    if data.get("kb_match") and isinstance(data["kb_match"], dict):
        # Ensure all required fields are present
        if not data["kb_match"].get("source_file"):
            data["kb_match"] = None

    return TriageResult.model_validate(data)


def triage_ticket(
    subject: str,
    body: str,
    ticket_id: str | None = None,
    account_id: str | None = None,
    company: str | None = None,
) -> TriageResult:
    """
    Triage a support ticket and return a structured result.

    Args:
        subject: Ticket subject line.
        body: Full ticket body text.
        ticket_id: Optional ticket ID for metadata.
        account_id: Optional account ID for metadata.
        company: Optional company name for metadata.

    Returns:
        TriageResult with classification, routing, and draft response.
    """
    # Step 1: Retrieve relevant KB context
    kb_results = retrieve_for_ticket(subject, body)
    kb_context = _format_kb_context(kb_results)

    # Step 2: Build the prompt
    metadata = {"ticket_id": ticket_id, "account_id": account_id, "company": company}
    user_prompt = format_triage_user_prompt(
        subject=subject,
        body=body,
        kb_context=kb_context,
        metadata=metadata,
    )

    # Step 3: Call the LLM
    client = _get_client()
    response = client.chat.completions.create(
        model=MODEL_NAME,
        temperature=TEMPERATURE,
        seed=SEED,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": TRIAGE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )

    # Step 4: Parse and validate
    raw_content = response.choices[0].message.content
    return _parse_triage_response(raw_content)


def triage_ticket_from_input(ticket_input: TicketInput) -> TriageResult:
    """Triage from a TicketInput model (used by the API)."""
    return triage_ticket(
        subject=ticket_input.subject,
        body=ticket_input.body,
        ticket_id=ticket_input.ticket_id,
        account_id=ticket_input.account_id,
        company=ticket_input.company,
    )


def triage_ticket_from_dataset(ticket_id: str) -> TriageResult:
    """Triage a ticket from the mock dataset by its ticket_id."""
    from src.config import get_ticket_by_id

    ticket = get_ticket_by_id(ticket_id)
    if not ticket:
        raise ValueError(f"Ticket {ticket_id} not found in dataset")

    return triage_ticket(
        subject=ticket["subject"],
        body=ticket["body"],
        ticket_id=ticket["ticket_id"],
        account_id=ticket.get("account_id"),
        company=ticket.get("company"),
    )


async def triage_ticket_stream(
    subject: str,
    body: str,
    ticket_id: str | None = None,
    account_id: str | None = None,
    company: str | None = None,
) -> AsyncGenerator[str, None]:
    """
    Stream the triage result token by token (bonus: streaming output).

    Yields partial JSON tokens as they arrive from the LLM.
    After streaming completes, yields the final validated JSON.
    """
    # Step 1: Retrieve relevant KB context
    kb_results = retrieve_for_ticket(subject, body)
    kb_context = _format_kb_context(kb_results)

    # Step 2: Build the prompt
    metadata = {"ticket_id": ticket_id, "account_id": account_id, "company": company}
    user_prompt = format_triage_user_prompt(
        subject=subject,
        body=body,
        kb_context=kb_context,
        metadata=metadata,
    )

    # Step 3: Stream from LLM
    client = _get_client()
    # For Groq, prompt MUST contain the word JSON in json_object mode
    # It is already in our user prompt ("Respond ONLY with valid JSON")

    stream = client.chat.completions.create(
        model=MODEL_NAME,
        temperature=TEMPERATURE,
        seed=SEED,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": TRIAGE_SYSTEM_PROMPT},
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

    # Yield final separator + validated result
    try:
        result = _parse_triage_response(full_content)
        yield "\n\n---VALIDATED---\n" + result.model_dump_json(indent=2)
    except Exception as e:
        yield f"\n\n---VALIDATION_ERROR---\n{str(e)}"

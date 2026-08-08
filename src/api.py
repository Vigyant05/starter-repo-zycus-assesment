"""
FastAPI REST API for the AI Support & TAM Tooling system.

Exposes endpoints for:
  - Ticket triage (sync + streaming)
  - Account health briefs (sync + streaming)
  - Prompt versioning info
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse

from src.triage.schemas import TicketInput, TriageResult
from src.triage.agent import triage_ticket_from_input, triage_ticket_from_dataset, triage_ticket_stream
from src.summariser.schemas import AccountBriefRequest, AccountBrief
from src.summariser.agent import generate_account_brief, generate_account_brief_stream
from src.triage.prompts import PROMPT_REGISTRY

app = FastAPI(
    title="AI Support & TAM Tooling",
    description="Production-grade AI for Technical Support & TAM Teams",
    version="1.0.0",
)


# ── Health Check ───────────────────────────────────────────────
@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


# ── Task 1: Ticket Triage ─────────────────────────────────────
@app.post("/triage", response_model=TriageResult)
async def triage(ticket: TicketInput):
    """
    Triage a support ticket.

    Accepts raw ticket text and returns structured classification,
    routing, and a draft response.
    """
    try:
        result = triage_ticket_from_input(ticket)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/triage/{ticket_id}", response_model=TriageResult)
async def triage_by_id(ticket_id: str):
    """Triage a ticket from the mock dataset by its ticket_id."""
    try:
        result = triage_ticket_from_dataset(ticket_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/triage/stream")
async def triage_stream(ticket: TicketInput):
    """
    Stream the triage result token by token (bonus: streaming output).

    Returns a Server-Sent Events stream.
    """
    return StreamingResponse(
        triage_ticket_stream(
            subject=ticket.subject,
            body=ticket.body,
            ticket_id=ticket.ticket_id,
            account_id=ticket.account_id,
            company=ticket.company,
        ),
        media_type="text/event-stream",
    )


# ── Task 2: Account Health Brief ──────────────────────────────
@app.post("/account-brief", response_model=AccountBrief)
async def account_brief(request: AccountBriefRequest):
    """
    Generate an account health brief for TAM QBR preparation.

    Accepts an account ID and returns a 3-section brief with
    executive summary, risk flags, and talking points.
    """
    try:
        result = generate_account_brief(request.account_id, days=request.days)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/account-brief/stream")
async def account_brief_stream(request: AccountBriefRequest):
    """
    Stream the account brief generation (bonus: streaming output).

    Returns a Server-Sent Events stream with status updates and the final brief.
    """
    return StreamingResponse(
        generate_account_brief_stream(request.account_id, days=request.days),
        media_type="text/event-stream",
    )


# ── Bonus: Prompt Versioning ──────────────────────────────────
@app.get("/prompts")
async def list_prompts():
    """
    List all registered prompt templates with their versions (bonus: prompt versioning).
    """
    summary = {}
    for name, info in PROMPT_REGISTRY.items():
        summary[name] = {
            "version": info["version"],
            "changelog": info["changelog"].strip(),
        }
    return JSONResponse(content=summary)

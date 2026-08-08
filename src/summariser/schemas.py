"""
Pydantic schemas for the TAM account health summariser.

Defines structured output models for the 3-section account brief
with risk flags and evidence-backed justifications.
"""

from enum import Enum
from pydantic import BaseModel, Field


class RiskSignalType(str, Enum):
    """Types of risk signals detected in ticket history."""

    CHURN_RISK = "churn_risk"
    ESCALATION = "escalation"
    PRODUCT_DISSATISFACTION = "product_dissatisfaction"
    ADOPTION_DECLINE = "adoption_decline"
    RENEWAL_RISK = "renewal_risk"


class RiskSeverity(str, Enum):
    """Severity of a detected risk signal."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RiskFlag(BaseModel):
    """A flagged risk signal with evidence from ticket data."""

    ticket_id: str = Field(description="Ticket ID that triggered this flag")
    signal_type: RiskSignalType = Field(description="Type of risk signal detected")
    severity: RiskSeverity = Field(description="Severity of the risk")
    justification: str = Field(
        description="Direct quote from the ticket body that justifies this flag"
    )
    recommendation: str = Field(
        description="Recommended action for the TAM"
    )


class AccountBrief(BaseModel):
    """
    Structured 3-section account health brief for TAM QBR preparation.

    Sections:
    1. Executive Summary (3-5 sentences)
    2. Open Risks & Flagged Issues
    3. Recommended Talking Points
    """

    account_id: str = Field(description="Account identifier")
    company: str = Field(description="Company name")
    executive_summary: str = Field(
        description="3-5 sentence executive summary of account health"
    )
    open_risks: list[RiskFlag] = Field(
        default_factory=list,
        description="Flagged tickets suggesting churn risk or escalation signals",
    )
    talking_points: list[str] = Field(
        default_factory=list,
        description="Recommended talking points for the TAM's next conversation",
    )

    # Metadata (not part of the LLM output, added post-processing)
    health_status: str | None = Field(default=None, description="Current health status from account data")
    arr_usd: int | None = Field(default=None, description="Annual recurring revenue")
    renewal_date: str | None = Field(default=None, description="Contract renewal date")
    tickets_analysed: int = Field(default=0, description="Number of tickets analysed")


class AccountBriefRequest(BaseModel):
    """Input schema for the account brief endpoint."""

    account_id: str = Field(description="Account ID to generate brief for")
    days: int = Field(default=90, description="Number of days of ticket history to consider")

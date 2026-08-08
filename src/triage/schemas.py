"""
Pydantic schemas for the ticket triage pipeline.

Defines structured output models that enforce valid enum values
for product areas, categories, and urgency tiers.
"""

from enum import Enum
from pydantic import BaseModel, Field


class IssueCategory(str, Enum):
    """Valid issue categories from the data schema."""

    BUG = "Bug"
    FEATURE_REQUEST = "Feature Request"
    HOW_TO = "How-To"
    PERFORMANCE = "Performance"
    BILLING = "Billing"
    INTEGRATION = "Integration"
    ONBOARDING = "Onboarding"
    DATA_LOSS = "Data Loss"


class UrgencyTier(str, Enum):
    """Urgency levels P1 (critical) through P4 (low)."""

    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


class Product(str, Enum):
    """Products in the platform."""

    DATABRIDGE_PRO = "DataBridge Pro"
    CLOUDSYNC = "CloudSync"
    ANALYTICSHUB = "AnalyticsHub"
    SECUREVAULT = "SecureVault"
    WORKFLOWENGINE = "WorkflowEngine"


class KBMatch(BaseModel):
    """A matched knowledge-base document."""

    source_file: str = Field(description="Path to the matched KB document")
    heading: str = Field(description="Relevant section heading in the document")
    relevance_summary: str = Field(description="Why this document is relevant to the ticket")


class TriageResult(BaseModel):
    """Structured triage output for a support ticket."""

    product: str = Field(description="Product the ticket relates to")
    product_area: str = Field(description="Module or area within the product")
    issue_category: IssueCategory = Field(description="Classification of the issue type")
    urgency_tier: UrgencyTier = Field(description="Priority level P1-P4")
    reasoning: str = Field(
        description="Brief explanation of why this classification was chosen"
    )
    kb_match: KBMatch | None = Field(
        default=None,
        description="Matched knowledge-base document, if any known issue pattern was found",
    )
    recommended_team: str = Field(
        description="Suggested responder team for this ticket"
    )
    draft_response: str = Field(
        description="Draft first-response message for the support agent to send"
    )


class TicketInput(BaseModel):
    """Input schema for the triage endpoint."""

    subject: str = Field(description="Ticket subject line")
    body: str = Field(description="Full ticket body text")
    ticket_id: str | None = Field(default=None, description="Optional ticket ID for reference")
    account_id: str | None = Field(default=None, description="Optional account ID")
    company: str | None = Field(default=None, description="Optional company name")

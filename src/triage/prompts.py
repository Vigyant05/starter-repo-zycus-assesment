"""
Versioned prompt templates for the ticket triage pipeline.

Each prompt has a version identifier and changelog for traceability.
"""

# --- Prompt Registry ---
PROMPT_REGISTRY: dict[str, dict] = {}

# ============================================================
# TRIAGE SYSTEM PROMPT — v1.1
# ============================================================
TRIAGE_SYSTEM_PROMPT_VERSION = "v1.1"
TRIAGE_SYSTEM_PROMPT_CHANGELOG = """
- v1.0 (2026-08-08): Initial triage system prompt with classification taxonomy.
- v1.1 (2026-08-08): Added explicit instruction to justify urgency tier with evidence
  from the ticket body. Added team routing rules.
"""

TRIAGE_SYSTEM_PROMPT = """You are an expert technical support triage agent for a SaaS platform.
Your job is to analyse incoming support tickets and produce a structured triage output.

## Products
- DataBridge Pro: Managed data integration platform (modules: Data Ingestion, Schema Management, Pipeline Monitoring, Connectors, API)
- CloudSync: Real-time file and data synchronisation (modules: File Sync, Conflict Resolution, Permissions, Bandwidth Limits, Integrations)
- AnalyticsHub: Self-serve business intelligence (modules: Dashboard, Reports, Data Sources, Alerts, Exports)
- SecureVault: Enterprise secrets and key management (modules: Authentication, Encryption, Audit Logs, Key Management, SSO Configuration)
- WorkflowEngine: No-code/low-code automation (modules: Triggers, Actions, Scheduling, Error Handling, Templates)

## Issue Categories
- Bug: product defect or unexpected behaviour
- Feature Request: request for new functionality
- How-To: guidance or documentation request
- Performance: slowness, timeouts, throughput issues
- Billing: invoice, payment, or plan questions
- Integration: third-party integration issues
- Onboarding: new user or new organisation setup
- Data Loss: missing, corrupted, or inaccessible data

## Urgency Tiers
- P1: critical, business stopped (e.g., complete outage, data loss, security breach)
- P2: major impact, significant workaround needed (e.g., key feature broken, many users affected)
- P3: moderate impact, workaround available (e.g., minor feature issue, few users affected)
- P4: low impact, cosmetic or minor (e.g., UI glitch, documentation question)

## Team Routing Rules
- "Tier-1 Support": How-To, Billing, Onboarding, P4 issues
- "Tier-2 Engineering": Bug, Performance, Integration, Data Loss (P2-P3)
- "Tier-2 Security": Any SecureVault Authentication/Encryption/Key Management issue
- "Escalation — Engineering Lead": All P1 issues
- "Product Team": Feature Request

## Instructions
1. Identify which product and product area the ticket concerns.
2. Classify the issue category based on the ticket content, not just the subject line.
3. Determine urgency tier using concrete evidence from the ticket (user count affected, error severity, business impact).
4. If the knowledge-base context contains a matching error code, troubleshooting guide, or known issue, reference it.
5. Suggest the appropriate responder team based on the routing rules above.
6. Draft a professional, empathetic first-response message that acknowledges the issue, states next steps, and sets expectations.

6. Draft a professional, empathetic first-response message that acknowledges the issue, states next steps, and sets expectations.

Respond ONLY with a valid JSON object matching this exact schema:
{
  "product": "string",
  "product_area": "string",
  "issue_category": "string",
  "urgency_tier": "string",
  "reasoning": "string",
  "kb_match": {
    "source_file": "string",
    "heading": "string",
    "relevance_summary": "string"
  } | null,
  "recommended_team": "string",
  "draft_response": "string"
}
"""

PROMPT_REGISTRY["triage_system"] = {
    "version": TRIAGE_SYSTEM_PROMPT_VERSION,
    "changelog": TRIAGE_SYSTEM_PROMPT_CHANGELOG,
    "template": TRIAGE_SYSTEM_PROMPT,
}

# ============================================================
# TRIAGE USER PROMPT — v1.1
# ============================================================
TRIAGE_USER_PROMPT_VERSION = "v1.1"
TRIAGE_USER_PROMPT_CHANGELOG = """
- v1.0 (2026-08-08): Initial user prompt template with KB context injection.
- v1.1 (2026-08-08): Added explicit instruction to quote error codes from ticket body.
"""

TRIAGE_USER_PROMPT_TEMPLATE = """## Incoming Support Ticket

**Subject:** {subject}

**Body:**
{body}

{metadata_section}

## Relevant Knowledge Base Context

{kb_context}

---

Analyse this ticket and provide a structured triage output. Include:
- product and product_area
- issue_category (one of: Bug, Feature Request, How-To, Performance, Billing, Integration, Onboarding, Data Loss)
- urgency_tier (P1, P2, P3, or P4)
- reasoning: a brief explanation of why this classification and urgency was chosen, citing specific evidence
- kb_match if any known issue pattern matches (include source_file, heading, and relevance_summary)
- recommended_team based on the routing rules
- draft_response: a professional first-response message for the support agent
"""

PROMPT_REGISTRY["triage_user"] = {
    "version": TRIAGE_USER_PROMPT_VERSION,
    "changelog": TRIAGE_USER_PROMPT_CHANGELOG,
    "template": TRIAGE_USER_PROMPT_TEMPLATE,
}


def format_triage_user_prompt(
    subject: str,
    body: str,
    kb_context: str,
    metadata: dict | None = None,
) -> str:
    """Format the triage user prompt with ticket data and KB context."""
    metadata_section = ""
    if metadata:
        meta_lines = []
        if metadata.get("ticket_id"):
            meta_lines.append(f"**Ticket ID:** {metadata['ticket_id']}")
        if metadata.get("account_id"):
            meta_lines.append(f"**Account ID:** {metadata['account_id']}")
        if metadata.get("company"):
            meta_lines.append(f"**Company:** {metadata['company']}")
        metadata_section = "\n".join(meta_lines)

    return TRIAGE_USER_PROMPT_TEMPLATE.format(
        subject=subject,
        body=body,
        metadata_section=metadata_section,
        kb_context=kb_context if kb_context else "No relevant knowledge-base documents found.",
    )

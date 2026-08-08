# US Delivery Internship — Starter Dataset

This repository contains the mock dataset for the **US Delivery Internship Technical Task Round**.  
Candidates should use this data exclusively for their submissions.

---

## Repository Structure

```
starter-repo/
├── data/
│   ├── tickets.json          # 500 synthetic support tickets
│   └── accounts.json         # 50 synthetic customer account summaries
├── knowledge-base/
│   ├── products/
│   │   ├── databridge-pro.md
│   │   ├── cloudsync.md
│   │   ├── analyticshub.md
│   │   ├── securevault.md
│   │   └── workflowengine.md
│   ├── troubleshooting/
│   │   ├── authentication-sso.md
│   │   └── performance-and-integrations.md
│   ├── billing/
│   │   └── billing-and-plans.md
│   └── onboarding/
│       └── onboarding-guide.md
└── DATA_SCHEMA.md            # Field-level schema documentation
```

---

## Data Description

### `data/tickets.json`

500 synthetic support tickets submitted by fictitious enterprise customers. Each ticket represents a realistic interaction between a customer and the technical support team.

**Key fields:**

| Field | Type | Description |
|-------|------|-------------|
| `ticket_id` | string | Unique ticket identifier (e.g., `TKT-10042`) |
| `account_id` | string | Links to an account in `accounts.json` |
| `company` | string | Customer company name |
| `subject` | string | Ticket subject line |
| `body` | string | Full ticket body text |
| `product` | string | Product the ticket relates to |
| `product_area` | string | Module within the product |
| `category` | string | Issue type: Bug, Feature Request, How-To, Performance, Billing, Integration, Onboarding, Data Loss |
| `urgency` | string | P1 (critical) to P4 (low) |
| `status` | string | Open, In Progress, Pending Customer, Resolved, Closed |
| `plan_tier` | string | Starter, Professional, Business, Enterprise |
| `assigned_agent` | string | Support agent name |
| `created_at` | ISO 8601 | Ticket creation timestamp |
| `updated_at` | ISO 8601 | Last update timestamp |
| `tags` | array | Free-form tags |
| `channel` | string | Submission channel: email, portal, chat, phone |
| `satisfaction_score` | int\|null | CSAT score 1–5, or null if not submitted |

See [DATA_SCHEMA.md](DATA_SCHEMA.md) for full schema with examples.

---

### `data/accounts.json`

50 synthetic customer account summaries, each representing a fictional enterprise customer's relationship with the platform.

**Key fields:**

| Field | Type | Description |
|-------|------|-------------|
| `account_id` | string | Unique account identifier |
| `company` | string | Company name |
| `tam` | string | Assigned Technical Account Manager |
| `plan_tier` | string | Current plan |
| `arr_usd` | int | Annual recurring revenue in USD |
| `seats_licensed` | int | Number of licensed seats |
| `seats_active` | int | Seats with activity in last 30 days |
| `products` | array | Products in use |
| `health_status` | string | Healthy, At Risk, Churning, or New |
| `usage_trend` | string | Increasing, Stable, Declining, or Inactive |
| `open_tickets` | int | Currently open support tickets |
| `p1_tickets_last_30d` | int | P1 tickets in last 30 days |
| `renewal_date` | YYYY-MM-DD | Contract renewal date |
| `last_qbr_date` | YYYY-MM-DD | Date of last Quarterly Business Review |
| `escalation_notes` | array | Free-text escalation observations |
| `nps_score` | int\|null | Net Promoter Score 1–10, or null |
| `primary_contact` | object | `name` and `title` of main contact |
| `integrations_active` | array | Active third-party integrations |
| `region` | string | Geographic region |
| `industry` | string | Customer industry vertical |

---

### `knowledge-base/`

Markdown documentation files representing a product knowledge base. These docs contain:

- Product feature descriptions and configuration references
- Common error codes and their meanings
- Step-by-step troubleshooting guides
- Plan limits and pricing information
- Onboarding checklists and training paths

Candidates should use these docs as the retrieval corpus for knowledge-base lookup features.

---

## Usage Notes

- All data is **entirely synthetic**. Company names, contact details, and ticket content are fictional.
- Ticket `account_id` values do not always match an entry in `accounts.json` — this is intentional. Handle missing account lookups gracefully.
- The `escalation_notes` field in accounts contains plain-text observations. These are designed to test churn-risk signal detection.
- Some tickets are deliberately ambiguous in category or urgency — this tests edge-case handling.

---

## Setup Instructions

1. **Install dependencies:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   Copy `.env.example` to `.env` and set your API keys:
   ```bash
   cp .env.example .env
   # Edit .env and set GROQ_API_KEY
   ```

3. **Index the knowledge base:**
   Builds the local ChromaDB vector store for RAG.
   ```bash
   python main.py index
   ```

---

## Running the Application

### 1. Streamlit UI (Bonus)
The easiest way to interact with both Task 1 and Task 2:
```bash
python main.py ui
```
This will open a local web app with tabs for Ticket Triage and TAM Account Brief, featuring streaming output.

### 2. FastAPI Server
Run the REST API:
```bash
python main.py serve
```
The API documentation (Swagger UI) is available at `http://localhost:8000/docs`.

### 3. CLI Evaluation Harness (Task 3)
Run the automated test suite with rule-based and LLM-as-judge scoring:
```bash
python main.py eval
```
This will generate `eval_report.json` and `eval_report.md` in the root directory.

---

## Sample Runs

### Task 1: Ticket Triage
```bash
curl -X POST http://localhost:8000/triage \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "Unable to connect DataBridge Pro to Connectors",
    "body": "We are getting ERR_CONNECTION_TIMEOUT after 30s. This is impacting 47 users."
  }'
```

### Task 2: Account Brief
```bash
curl -X POST http://localhost:8000/account-brief \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": "ACC-3847",
    "days": 90
  }'
```

---

## Design Note

Read the answers to the architectural and design questions (Failure Modes, Latency vs Quality, Data Sensitivity, Scaling) here:
[DESIGN_NOTE.md](DESIGN_NOTE.md)

---

## Bonus Features Implemented

*   **+5 marks:** Thin UI demo using Streamlit (`python main.py ui`).
*   **+3 marks:** Streaming output implemented for both Task 1 and Task 2 via FastAPI `StreamingResponse` and Streamlit `st.write_stream`.
*   **+2 marks:** Automated CI step using GitHub Actions (`.github/workflows/eval.yml`).
*   **+2 marks:** Prompt versioning implemented in `prompts.py` and exposed via `GET /prompts`.

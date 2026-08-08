import streamlit as st
import sys
from pathlib import Path

# Add project root to sys.path so we can import src modules
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

from src.config import load_tickets, get_account_map
from src.triage.agent import triage_ticket_stream, triage_ticket
from src.summariser.agent import generate_account_brief_stream, generate_account_brief
import json

st.set_page_config(
    page_title="AI Support & TAM Tooling",
    page_icon="🛠️",
    layout="wide",
)

st.title("🛠️ AI Support & TAM Tooling")

tab1, tab2 = st.tabs(["🎫 Ticket Triage", "📈 TAM Account Brief"])

# --- Tab 1: Ticket Triage ---
with tab1:
    st.header("Intelligent Ticket Triage")
    st.markdown("Classifies, routes, and drafts responses for support tickets.")

    # Select ticket source
    tickets = load_tickets()
    ticket_options = ["Custom Input"] + [f"{t['ticket_id']} - {t['subject']}" for t in tickets[:50]]
    
    selected_ticket = st.selectbox("Select a ticket to triage:", ticket_options)
    
    subject_input = ""
    body_input = ""
    ticket_id = None
    account_id = None
    company = None

    if selected_ticket == "Custom Input":
        subject_input = st.text_input("Subject")
        body_input = st.text_area("Body", height=200)
    else:
        # Extract ID and find ticket
        t_id = selected_ticket.split(" - ")[0]
        ticket = next((t for t in tickets if t["ticket_id"] == t_id), None)
        if ticket:
            st.info(f"**Subject:** {ticket['subject']}")
            st.text(ticket['body'])
            subject_input = ticket['subject']
            body_input = ticket['body']
            ticket_id = ticket['ticket_id']
            account_id = ticket.get('account_id')
            company = ticket.get('company')

    use_streaming = st.checkbox("Use streaming output", value=True, key="triage_stream_toggle")

    if st.button("Triage Ticket", type="primary", disabled=not subject_input):
        with st.spinner("Analyzing ticket..."):
            
            if use_streaming:
                import asyncio
                
                async def run_triage_stream():
                    result_placeholder = st.empty()
                    full_response = ""
                    validated_json = None
                    
                    async for token in triage_ticket_stream(
                        subject=subject_input, 
                        body=body_input,
                        ticket_id=ticket_id,
                        account_id=account_id,
                        company=company
                    ):
                        if token.startswith("\n\n---VALIDATED---\n"):
                            validated_json = token.split("---VALIDATED---\n")[1]
                            break
                        elif token.startswith("\n\n---VALIDATION_ERROR---\n"):
                            st.error(f"Validation Error: {token}")
                            break
                        else:
                            full_response += token
                            # Simple formatting for the raw stream
                            formatted = f"```json\n{full_response}\n```"
                            result_placeholder.markdown(formatted)
                    
                    if validated_json:
                        # Clear raw stream and show structured output
                        result_placeholder.empty()
                        data = json.loads(validated_json)
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Product", f"{data['product']} ({data['product_area']})")
                            st.metric("Category", data['issue_category'])
                        with col2:
                            st.metric("Urgency", data['urgency_tier'])
                            st.metric("Route To", data['recommended_team'])
                        
                        st.subheader("Reasoning")
                        st.write(data['reasoning'])
                        
                        if data.get('kb_match'):
                            st.subheader("Knowledge Base Match")
                            kb = data['kb_match']
                            st.success(f"**{kb['source_file']}** ({kb['heading']})\n\n{kb['relevance_summary']}")
                        
                        st.subheader("Draft Response")
                        st.info(data['draft_response'])
                
                asyncio.run(run_triage_stream())
                
            else:
                # Sync version
                result = triage_ticket(
                    subject=subject_input, 
                    body=body_input,
                    ticket_id=ticket_id,
                    account_id=account_id,
                    company=company
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Product", f"{result.product} ({result.product_area})")
                    st.metric("Category", result.issue_category.value)
                with col2:
                    st.metric("Urgency", result.urgency_tier.value)
                    st.metric("Route To", result.recommended_team)
                
                st.subheader("Reasoning")
                st.write(result.reasoning)
                
                if result.kb_match:
                    st.subheader("Knowledge Base Match")
                    st.success(f"**{result.kb_match.source_file}** ({result.kb_match.heading})\n\n{result.kb_match.relevance_summary}")
                
                st.subheader("Draft Response")
                st.info(result.draft_response)


# --- Tab 2: Account Brief ---
with tab2:
    st.header("TAM Account Health Summariser")
    st.markdown("Generates a concise account brief based on account data and ticket history.")
    
    account_map = get_account_map()
    account_options = [f"{acc_id} - {acc['company']}" for acc_id, acc in account_map.items()]
    
    selected_account = st.selectbox("Select an Account:", account_options)
    
    use_streaming_brief = st.checkbox("Use streaming output", value=True, key="brief_stream_toggle")
    
    if st.button("Generate Brief", type="primary"):
        acc_id = selected_account.split(" - ")[0]
        
        with st.spinner(f"Analyzing account {acc_id}..."):
            
            if use_streaming_brief:
                import asyncio
                
                async def run_brief_stream():
                    status_placeholder = st.empty()
                    result_placeholder = st.empty()
                    full_response = ""
                    validated_json = None
                    
                    async for token in generate_account_brief_stream(account_id=acc_id):
                        if token.startswith("{") and "status" in token:
                            # It's a status update
                            try:
                                status_data = json.loads(token.strip())
                                status = status_data.get("status")
                                if status == "loading_tickets":
                                    status_placeholder.info(f"Loading ticket history for {status_data.get('company')}...")
                                elif status == "tickets_loaded":
                                    status_placeholder.info(f"Loaded {status_data.get('count')} tickets. Extracting risks...")
                                elif status == "risks_extracted":
                                    count = status_data.get('risk_count', 0)
                                    if count > 0:
                                        status_placeholder.warning(f"Found {count} risk signals. Synthesizing brief...")
                                    else:
                                        status_placeholder.success("No risk signals found. Synthesizing brief...")
                            except json.JSONDecodeError:
                                pass
                        
                        elif token.startswith("\n\n---VALIDATED---\n"):
                            validated_json = token.split("---VALIDATED---\n")[1]
                            break
                        elif token.startswith("\n\n---VALIDATION_ERROR---\n"):
                            st.error(f"Validation Error: {token}")
                            break
                        else:
                            # It's part of the LLM stream
                            full_response += token
                            formatted = f"```json\n{full_response}\n```"
                            result_placeholder.markdown(formatted)
                    
                    if validated_json:
                        status_placeholder.empty()
                        result_placeholder.empty()
                        data = json.loads(validated_json)
                        
                        st.subheader(f"Account Brief: {data['company']}")
                        
                        col1, col2, col3, col4 = st.columns(4)
                        col1.metric("Health", data['health_status'])
                        col2.metric("ARR", f"${data['arr_usd']:,}")
                        col3.metric("Renewal", data['renewal_date'])
                        col4.metric("Tickets Analysed", data['tickets_analysed'])
                        
                        st.markdown("### Executive Summary")
                        st.write(data['executive_summary'])
                        
                        st.markdown("### Talking Points")
                        for point in data['talking_points']:
                            st.markdown(f"- {point}")
                        
                        st.markdown(f"### Open Risks ({len(data['open_risks'])})")
                        if not data['open_risks']:
                            st.success("No significant risk signals detected.")
                        else:
                            for risk in data['open_risks']:
                                color = "red" if risk['severity'] == "high" else "orange" if risk['severity'] == "medium" else "blue"
                                st.markdown(f"**:{color}[{risk['severity'].upper()} - {risk['signal_type']}]** (Ticket {risk['ticket_id']})")
                                st.markdown(f"> *\"{risk['justification']}\"*")
                                st.markdown(f"**TAM Action:** {risk['recommendation']}")
                                st.divider()
                
                asyncio.run(run_brief_stream())
                
            else:
                # Sync version
                brief = generate_account_brief(account_id=acc_id)
                
                st.subheader(f"Account Brief: {brief.company}")
                        
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Health", brief.health_status)
                col2.metric("ARR", f"${brief.arr_usd:,}")
                col3.metric("Renewal", brief.renewal_date)
                col4.metric("Tickets Analysed", brief.tickets_analysed)
                
                st.markdown("### Executive Summary")
                st.write(brief.executive_summary)
                
                st.markdown("### Talking Points")
                for point in brief.talking_points:
                    st.markdown(f"- {point}")
                
                st.markdown(f"### Open Risks ({len(brief.open_risks)})")
                if not brief.open_risks:
                    st.success("No significant risk signals detected.")
                else:
                    for risk in brief.open_risks:
                        severity_val = risk.severity.value
                        color = "red" if severity_val == "high" else "orange" if severity_val == "medium" else "blue"
                        st.markdown(f"**:{color}[{severity_val.upper()} - {risk.signal_type.value}]** (Ticket {risk.ticket_id})")
                        st.markdown(f"> *\"{risk.justification}\"*")
                        st.markdown(f"**TAM Action:** {risk.recommendation}")
                        st.divider()

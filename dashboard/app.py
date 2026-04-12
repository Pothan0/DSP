import streamlit as st
import requests
import json
import pandas as pd

API_BASE_URL = "http://localhost:7070/api/dashboard"

st.set_page_config(page_title="TrustChain Security Dashboard", layout="wide")

st.title("🛡️ TrustChain AI Security Gateway")

tab1, tab2, tab3 = st.tabs(["🚦 Live Traffic", "✋ HITL Queue", "🔍 Audit Explorer"])

def fetch_pending():
    try:
        response = requests.get(f"{API_BASE_URL}/pending")
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict) and "pending" in data:
                return data["pending"]
            return data
    except Exception as e:
        st.error(f"Error fetching pending requests: {e}")
    return []

def fetch_logs():
    try:
        response = requests.get(f"{API_BASE_URL}/logs")
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        st.error(f"Error fetching logs: {e}")
    return []

def resolve_request(req_id, approved):
    try:
        response = requests.post(
            f"{API_BASE_URL}/resolve/{req_id}",
            json={"approved": approved}
        )
        if response.status_code == 200:
            st.success(f"Request {req_id} {'approved' if approved else 'rejected'} successfully.")
        else:
            st.error(f"Failed to resolve request: {response.text}")
    except Exception as e:
        st.error(f"Error resolving request: {e}")

with tab1:
    st.header("Live Traffic Logs")
    logs = fetch_logs()
    if logs:
        df = pd.DataFrame(logs)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No recent logs found.")

with tab2:
    st.header("Human-in-the-Loop Review Queue")
    st.write("Requests blocked due to policy violations or low trust scores.")
    
    pending = fetch_pending()
    if not pending:
        st.success("No pending requests to review. Agent traffic is flowing normally.")
    else:
        for p in pending:
            req_id = p.get("message_id", p.get("id", str(p)))
            with st.expander(f"Review Required: {req_id}", expanded=True):
                st.json(p)
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Approve", key=f"approve_{req_id}"):
                        resolve_request(req_id, True)
                        st.rerun()
                with col2:
                    if st.button("❌ Reject", key=f"reject_{req_id}"):
                        resolve_request(req_id, False)
                        st.rerun()

with tab3:
    st.header("Audit Explorer")
    st.write("Deep dive into cryptographic audit trail.")
    logs = fetch_logs()
    if logs:
        st.json(logs)
    else:
        st.info("No audit trail available.")

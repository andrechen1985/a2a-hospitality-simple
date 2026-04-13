import os
import streamlit as st
import requests

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8001")
st.set_page_config(page_title="A2A Concierge", page_icon="robot")
st.title("AI Hospitality Concierge")
st.markdown("*100% Open Source - Rule-Based - No External LLM Required*")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "member_id" not in st.session_state:
    st.session_state.member_id = "GOLD_001"

with st.sidebar:
    st.header("Guest Profile")
    st.session_state.member_id = st.selectbox(
        "Member ID", ["GOLD_001", "SILVER_002", "NEW_GUEST"], index=0
    )
    show_trace = st.checkbox("Show A2A Protocol Trace", value=False)
    st.markdown("---")
    st.caption("Try: 'Can I check out at 2pm?'")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "trace" in msg and show_trace:
            with st.expander("A2A Trace"):
                st.json(msg["trace"])

if prompt := st.chat_input("Ask about checkout, amenities..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"), st.spinner("Consulting Hotel Ops..."):
        try:
            resp = requests.post(
                f"{BACKEND_URL}/chat",
                json={"user_message": prompt, "member_id": st.session_state.member_id, "show_trace": show_trace},
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            st.markdown(data["response"])
            msg = {"role": "assistant", "content": data["response"]}
            if data.get("trace"):
                msg["trace"] = data["trace"]
            st.session_state.messages.append(msg)
        except Exception as e:
            err = f"Error: {str(e)}\n\n*Check backend is running*"
            st.markdown(err)
            st.session_state.messages.append({"role": "assistant", "content": err})

st.markdown("---")
st.caption(f"Backend: `{BACKEND_URL}` | Logic: Rule-Based | 100% Open Source")

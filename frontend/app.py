import os
import streamlit as st
import requests

# 修復漏洞 9: 後端 URL 不暴露默認值，強制從環境變量獲取
BACKEND_URL = os.getenv("BACKEND_URL")
if not BACKEND_URL:
    raise ValueError("BACKEND_URL environment variable must be set")
st.set_page_config(page_title="A2A Concierge", page_icon="robot")

# Bilingual UI labels / 雙語介面標籤
UI_LABELS = {
    "title": {"en": "AI Hospitality Concierge", "zh": "AI 酒店禮賓服務"},
    "subtitle": {"en": "*100% Open Source - Rule-Based - No External LLM Required*", 
                 "zh": "*100% 開源 - 基於規則 - 無需外部 LLM*"},
    "guest_profile": {"en": "Guest Profile", "zh": "客人資料"},
    "member_id": {"en": "Member ID", "zh": "會員 ID"},
    # 修復漏洞 3: 移除 show_trace 標籤，因為功能已禁用
    "try_prompt": {"en": "Try: 'Can I check out at 2pm?'", "zh": "試試看：「我可以下午 2 點退房嗎？」"},
    "chat_input": {"en": "Ask about checkout, amenities...", "zh": "詢問退房、設施等問題..."},
    "consulting": {"en": "Consulting Hotel Ops...", "zh": "正在查詢酒店服務..."},
    "error_msg": {"en": "Error: ", "zh": "錯誤："},
    "check_backend": {"en": "*Check backend is running*", "zh": "*請檢查後端是否運行*"},
    "footer_backend": {"en": "Backend:", "zh": "後端："},
    "footer_logic": {"en": "Logic: Rule-Based | 100% Open Source", 
                     "zh": "邏輯：基於規則 | 100% 開源"},
}

def detect_ui_language():
    """Detect UI language based on session state or default to English"""
    if "ui_language" not in st.session_state:
        st.session_state.ui_language = "en"
    return st.session_state.ui_language

def get_label(key):
    """Get bilingual label based on current UI language"""
    lang = detect_ui_language()
    labels = UI_LABELS.get(key, {"en": key, "zh": key})
    return labels.get(lang, labels["en"])

st.title(get_label("title"))
st.markdown(get_label("subtitle"))

if "messages" not in st.session_state:
    st.session_state.messages = []
if "member_id" not in st.session_state:
    st.session_state.member_id = "GOLD_001"

with st.sidebar:
    st.header(get_label("guest_profile"))
    
    # Language selector / 語言選擇器
    st.subheader("Language / 語言")
    st.session_state.ui_language = st.radio(
        "UI Language",
        ["English", "中文"],
        index=0 if st.session_state.ui_language == "en" else 1,
        label_visibility="collapsed"
    )
    st.session_state.ui_language = "en" if st.session_state.ui_language == "English" else "zh"
    
    st.session_state.member_id = st.selectbox(
        get_label("member_id"), ["GOLD_001", "SILVER_002", "NEW_GUEST"], index=0
    )
    # 修復漏洞 3: 移除 show_trace 選項，因為後端已不再支持
    st.markdown("---")
    st.caption(get_label("try_prompt"))

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        # 修復漏洞 3: 移除 trace 顯示功能

if prompt := st.chat_input(get_label("chat_input")):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"), st.spinner(get_label("consulting")):
        try:
            resp = requests.post(
                f"{BACKEND_URL}/chat",
                json={"user_message": prompt, "member_id": st.session_state.member_id},
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            st.markdown(data["response"])
            msg = {"role": "assistant", "content": data["response"]}
            # 修復漏洞 3: 不再處理 trace 數據
            st.session_state.messages.append(msg)
        except Exception as e:
            err = f"{get_label('error_msg')}{str(e)}\n\n{get_label('check_backend')}"
            st.markdown(err)
            st.session_state.messages.append({"role": "assistant", "content": err})

st.markdown("---")
st.caption(f"{get_label('footer_backend')} `{BACKEND_URL}` | {get_label('footer_logic')}")

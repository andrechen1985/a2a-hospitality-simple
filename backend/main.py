import os
import json
import re
import uuid
import random
from datetime import datetime
from typing import Literal, Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pathlib import Path

# 動態偵測資料夾路徑 (相容本機開發與 Docker)
SCRIPT_DIR = Path(__file__).parent
if (SCRIPT_DIR.parent / "data").exists():
    DATA_DIR = SCRIPT_DIR.parent / "data"
else:
    DATA_DIR = SCRIPT_DIR / "data"

app = FastAPI(title="A2A Hospitality Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 對話歷史儲存（記憶體中，生產環境建議使用 Redis）
conversation_history: dict[str, list[dict]] = {}


def load_policy() -> dict:
    """載入政策文件，支持多語言模板變體"""
    import re
    policy = {}
    current_section = None
    with open(DATA_DIR / "policy.txt", "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("[") and line.endswith("]"):
                current_section = line[1:-1]
                policy[current_section] = {}
            elif ":" in line and current_section:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()
                # 處理多行模板（使用 | 分隔多個變體，每個變體以 emoji 開頭）
                if "_variants_" in key:
                    # 使用正則表達式在 emoji 之間的 | 處分割
                    variants = re.split(r'\s*\|\s*(?=[🎉✅⏳📋🔍⏰🙏😔💬🤝✨👍🤔❓🧐💭])', value)
                    variants = [v.strip() for v in variants if v.strip()]
                    policy[current_section][key] = variants
                else:
                    policy[current_section][key] = value
    return policy


def load_members() -> dict:
    with open(DATA_DIR / "members.json", "r") as f:
        return json.load(f)


POLICY = load_policy()
MEMBERS = load_members()

class A2ARequest(BaseModel):
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sender: str
    receiver: str
    intent: str
    member_id: str
    requested_time: Optional[str] = None


class A2AResponse(BaseModel):
    message_id: str
    status: Literal["success", "needs_approval", "denied", "error"]
    checkout_time: Optional[str] = None
    reason: str
    template_key: str = "error"


def get_time_greeting() -> str:
    """根據當前時段返回問候語"""
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "早上好"
    elif 12 <= hour < 14:
        return "午安"
    elif 14 <= hour < 18:
        return "下午好"
    elif 18 <= hour < 22:
        return "晚上好"
    else:
        return "夜深了"


def get_personalized_tone(tier: str, stay_count: int) -> str:
    """根據會員等級和停留次數調整語氣"""
    if tier == "Gold" and stay_count >= 10:
        return "vip"
    elif tier == "Gold":
        return "friendly"
    elif tier == "Silver":
        return "warm"
    else:
        return "standard"


def detect_language(message: str) -> str:
    """檢測用戶訊息的語言 (中文或英文)"""
    # 簡單的中文檢測：如果包含中文字符則視為中文
    chinese_chars = re.findall(r'[\u4e00-\u9fff]', message)
    if len(chinese_chars) > 0:
        return "zh"
    return "en"


def select_template_variants(template_key: str, tone: str, language: str = "zh") -> str:
    """從多個變體中選擇一個模板，考慮語氣、語言和隨機性"""
    # 根據語言選擇對應的變體 key
    variants_key = f"{template_key}_variants_{language}"
    
    # 如果有定義變體，從中選擇
    if variants_key in POLICY.get("RESPONSE_TEMPLATES", {}):
        variants = POLICY["RESPONSE_TEMPLATES"][variants_key]
        # 根據語氣過濾或直接隨機選擇
        return random.choice(variants)
    
    # 回退到單一模板（優先使用對應語言的預設模板）
    templates = POLICY.get("RESPONSE_TEMPLATES", {})
    lang_template_key = f"{template_key}_{language}"
    if lang_template_key in templates:
        return templates[lang_template_key]
    
    # 最終回退到通用 error
    return templates.get("error", "抱歉，我無法處理您的請求。" if language == "zh" else "Sorry, I cannot process your request.")


def agent_b_process(request: A2ARequest) -> A2AResponse:
    member = MEMBERS.get(request.member_id)
    if not member:
        return A2AResponse(message_id=request.message_id, status="error", reason="Member not found", template_key="error")
    
    tier = member["tier"]
    stay_count = member.get("stay_count", 0)
    requested = request.requested_time or "14:00"
    
    if request.intent == "late_checkout":
        tier_policy = POLICY["MEMBER_TIERS"].get(tier, "")
        rules = dict(item.strip().split("=") for item in tier_policy.split(",") if "=" in item)
        limit_time = rules.get("late_checkout_until", "11:00")
        auto_approve = rules.get("auto_approve", "false").lower() == "true"
        
        if requested <= limit_time:
            status_key = "success" if auto_approve else "needs_approval"
            return A2AResponse(
                message_id=request.message_id, 
                status=status_key, 
                checkout_time=requested, 
                reason=f"{tier} tier limit: {limit_time}", 
                template_key=status_key,
            )
        return A2AResponse(
            message_id=request.message_id, 
            status="denied", 
            reason=f"Exceeds {tier} limit ({limit_time})", 
            template_key="denied"
        )
    return A2AResponse(message_id=request.message_id, status="error", reason="Unsupported intent", template_key="error")

def parse_intent(message: str, member_id: str) -> A2ARequest:
    msg = message.lower()
    # 檢測延遲退房 (支持中英文)
    if any(kw in msg for kw in ["late checkout", "check out late", "2pm", "14:00", "下午", "晚點退房", "延遲退房", "晚退房"]):
        intent = "late_checkout"
        time_match = re.search(r'(\d{1,2}:\d{2})', message)
        requested_time = time_match.group(1) if time_match else "14:00"
    # 檢測提早入住 (支持中英文)
    elif any(kw in msg for kw in ["early checkin", "early check-in", "提早入住", "提前入住"]):
        intent = "early_checkin"
        requested_time = "12:00"
    else:
        intent = "general_inquiry"
        requested_time = None
    return A2ARequest(sender="AgentA", receiver="AgentB", intent=intent, member_id=member_id, requested_time=requested_time)


def format_guest_response(a2a_resp: A2AResponse, member_name: str, member_tier: str, stay_count: int, user_message: str = "", conversation_context: Optional[dict] = None) -> str:
    """
    格式化回應，整合：
    1. 時段問候語
    2. 個性化語氣
    3. 多樣化模板變體 (支持中英文)
    4. 對話歷史上下文
    """
    # 檢測用戶訊息的語言
    language = detect_language(user_message)
    
    # 獲取時段問候 (根據語言調整)
    greeting = get_time_greeting()
    if language == "en":
        hour = datetime.now().hour
        if 5 <= hour < 12:
            greeting = "Good morning"
        elif 12 <= hour < 14:
            greeting = "Good afternoon"
        elif 14 <= hour < 18:
            greeting = "Good afternoon"
        elif 18 <= hour < 22:
            greeting = "Good evening"
        else:
            greeting = "Good evening"
    
    # 獲取個性化語氣
    tone = get_personalized_tone(member_tier, stay_count)
    
    # 選擇模板（支持多變體和多語言）
    template = select_template_variants(a2a_resp.template_key, tone, language)
    
    # 根據語氣和語言添加前綴或後綴
    tone_prefix = ""
    tone_suffix = ""
    
    if tone == "vip":
        if language == "zh":
            prefixes = ["尊敬的", "珍貴的 VIP 會員", "我們最尊貴的"]
            suffixes = ["感謝您一直以來的支持！", "期待繼續為您提供優質服務！", "您的滿意是我們最大的動力！"]
        else:
            prefixes = ["Dear valued", "Esteemed VIP", "Our most distinguished"]
            suffixes = ["Thank you for your continued support!", "We look forward to serving you!", "Your satisfaction is our priority!"]
        tone_prefix = f"{random.choice(prefixes)} {member_name}, {greeting}!"
        tone_suffix = random.choice(suffixes)
    elif tone == "friendly":
        if language == "zh":
            prefixes = ["嗨", "哈囉", "親愛的"]
        else:
            prefixes = ["Hi", "Hello", "Dear"]
        tone_prefix = f"{random.choice(prefixes)} {member_name}, {greeting}!"
    elif tone == "warm":
        if language == "zh":
            prefixes = ["您好", "歡迎", "感謝光臨"]
        else:
            prefixes = ["Hello", "Welcome", "Thank you for staying with us"]
        if language == "zh":
            tone_prefix = f"{random.choice(prefixes)}，{member_name}，{greeting}！"
        else:
            tone_prefix = f"{random.choice(prefixes)}, {member_name}. {greeting}!"
    else:
        if language == "zh":
            tone_prefix = f"{member_name} 您好，{greeting}！"
        else:
            tone_prefix = f"Hello {member_name}, {greeting}!"
    
    # 格式化主要訊息
    main_message = template.format(name=member_name, time=a2a_resp.checkout_time or "", reason=a2a_resp.reason)
    
    # 組合完整回應
    if tone_suffix:
        return f"{tone_prefix}\n\n{main_message}\n\n{tone_suffix}"
    else:
        return f"{tone_prefix}\n\n{main_message}"


# 對話歷史管理函數
def update_conversation_history(member_id: str, user_message: str, bot_response: str, intent: str, status: str):
    """更新對話歷史"""
    if member_id not in conversation_history:
        conversation_history[member_id] = []
    
    # 限制歷史記錄數量（最多 10 條）
    if len(conversation_history[member_id]) >= 10:
        conversation_history[member_id].pop(0)
    
    conversation_history[member_id].append({
        "timestamp": datetime.now().isoformat(),
        "user_message": user_message,
        "bot_response": bot_response,
        "intent": intent,
        "status": status
    })


def get_conversation_context(member_id: str) -> Optional[dict]:
    """獲取最近的對話上下文"""
    if member_id in conversation_history and conversation_history[member_id]:
        return conversation_history[member_id][-1]
    return None

class ChatRequest(BaseModel):
    user_message: str
    member_id: str = "GOLD_001"
    show_trace: bool = False

class ChatResponse(BaseModel):
    response: str
    trace: Optional[dict] = None
    conversation_context: Optional[dict] = None

@app.post("/chat")
async def chat(req: ChatRequest):
    # 獲取會員資訊
    member = MEMBERS.get(req.member_id, {})
    member_name = member.get("name", "Guest")
    member_tier = member.get("tier", "Regular")
    stay_count = member.get("stay_count", 0)
    
    # 獲取對話上下文
    context = get_conversation_context(req.member_id)
    
    # 處理請求
    a2a_req = parse_intent(req.user_message, req.member_id)
    a2a_resp = agent_b_process(a2a_req)
    
    # 生成個性化回應 (傳入用戶訊息以檢測語言)
    guest_msg = format_guest_response(a2a_resp, member_name, member_tier, stay_count, req.user_message, context)
    
    # 更新對話歷史
    update_conversation_history(
        member_id=req.member_id,
        user_message=req.user_message,
        bot_response=guest_msg,
        intent=a2a_req.intent,
        status=a2a_resp.status
    )
    
    result = {"response": guest_msg}
    if req.show_trace:
        result["trace"] = {
            "a2a_request": a2a_req.model_dump(), 
            "a2a_response": a2a_resp.model_dump(),
            "member_info": {"name": member_name, "tier": member_tier, "stay_count": stay_count},
            "tone": get_personalized_tone(member_tier, stay_count),
            "greeting_time": get_time_greeting()
        }
        result["conversation_context"] = context
    
    return ChatResponse(**result)

@app.get("/health")
async def health():
    return {"status": "healthy", "agents": ["AgentA", "AgentB"], "logic": "rule-based"}

@app.get("/")
async def root():
    return {"status": "ok", "service": "a2a-hospitality-concierge"}

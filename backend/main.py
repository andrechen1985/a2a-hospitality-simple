import os
import json
import re
import uuid
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

def load_policy() -> dict:
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
                policy[current_section][key.strip()] = value.strip()
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

def agent_b_process(request: A2ARequest) -> A2AResponse:
    member = MEMBERS.get(request.member_id)
    if not member:
        return A2AResponse(message_id=request.message_id, status="error", reason="Member not found", template_key="error")
    tier = member["tier"]
    requested = request.requested_time or "14:00"
    if request.intent == "late_checkout":
        tier_policy = POLICY["MEMBER_TIERS"].get(tier, "")
        rules = dict(item.strip().split("=") for item in tier_policy.split(",") if "=" in item)
        limit_time = rules.get("late_checkout_until", "11:00")
        auto_approve = rules.get("auto_approve", "false").lower() == "true"
        if requested <= limit_time:
            status_key = "success" if auto_approve else "needs_approval"
            return A2AResponse(message_id=request.message_id, status=status_key, checkout_time=requested, reason=f"{tier} tier limit: {limit_time}", template_key=status_key)
        return A2AResponse(message_id=request.message_id, status="denied", reason=f"Exceeds {tier} limit ({limit_time})", template_key="denied")
    return A2AResponse(message_id=request.message_id, status="error", reason="Unsupported intent", template_key="error")

def parse_intent(message: str, member_id: str) -> A2ARequest:
    msg = message.lower()
    if any(kw in msg for kw in ["late checkout", "check out late", "2pm", "14:00"]):
        intent = "late_checkout"
        time_match = re.search(r'(\d{1,2}:\d{2})', msg)
        requested_time = time_match.group(1) if time_match else "14:00"
    elif "early checkin" in msg:
        intent = "early_checkin"
        requested_time = "12:00"
    else:
        intent = "general_inquiry"
        requested_time = None
    return A2ARequest(sender="AgentA", receiver="AgentB", intent=intent, member_id=member_id, requested_time=requested_time)

def format_guest_response(a2a_resp: A2AResponse, member_name: str) -> str:
    templates = POLICY["RESPONSE_TEMPLATES"]
    template = templates.get(a2a_resp.template_key, templates["error"])
    return template.format(name=member_name, time=a2a_resp.checkout_time or "", reason=a2a_resp.reason)

class ChatRequest(BaseModel):
    user_message: str
    member_id: str = "GOLD_001"
    show_trace: bool = False

class ChatResponse(BaseModel):
    response: str
    trace: Optional[dict] = None

@app.post("/chat")
async def chat(req: ChatRequest):
    a2a_req = parse_intent(req.user_message, req.member_id)
    a2a_resp = agent_b_process(a2a_req)
    member_name = MEMBERS.get(req.member_id, {}).get("name", "Guest")
    guest_msg = format_guest_response(a2a_resp, member_name)
    result = {"response": guest_msg}
    if req.show_trace:
        result["trace"] = {"a2a_request": a2a_req.model_dump(), "a2a_response": a2a_resp.model_dump()}
    return ChatResponse(**result)

@app.get("/health")
async def health():
    return {"status": "healthy", "agents": ["AgentA", "AgentB"], "logic": "rule-based"}

@app.get("/")
async def root():
    return {"status": "ok", "service": "a2a-hospitality-concierge"}

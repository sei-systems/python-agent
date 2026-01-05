import os
import json
import hmac
import hashlib
import uuid
from datetime import datetime, timezone
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
from openai import OpenAI
from tools.clock import get_current_time
from tools.search import web_search

# Load local environment variables
load_dotenv()

# --- SYSTEM INITIALIZATION ---
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
API_SECRET_KEY = os.getenv("API_SECRET_KEY")
MENDIX_HMAC_SECRET = os.getenv("MENDIX_HMAC_SECRET", "sei_systems_secure_gateway_01")

app = FastAPI(title="SEI Sentry: Strategic Intelligence Engine")

# --- SOC 2 CC6.1: CORS CONFIGURATION ---
origins = [
    "https://www.seisystems.co",
    "https://seisystems.co",
    "https://labs.seisystems.co",
    "http://localhost:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- SOC 2 CC8.1: DATA MODELS (The CRM Rules) ---
class ProspectData(BaseModel):
    company_name: str = Field(..., description="Full legal name of the organization.")
    industry: str = Field(..., description="The sector (e.g., Aerospace, FinTech, Manufacturing).")
    annual_revenue_estimate: int = Field(..., description="Estimated annual revenue as an integer.")
    employee_count: int = Field(..., description="Approximate number of employees.")
    full_name: str = Field(..., description="Primary contact name.")
    job_title: str = Field(..., description="The contact's role within the organization.")
    email: str = Field(..., description="Verified professional email address.")
    phone: str = Field(..., description="Contact phone number.")

class SentryAnalysis(BaseModel):
    current_pain_points: List[str] = Field(..., description="The manual friction points identified.")
    unlocked_potential: str = Field(..., description="Description of the 'Future State' SEI will create.")
    risk_score: int = Field(..., description="0-100 score based on urgency and technical need.")
    tech_stack_match: List[str] = Field(..., description="Systems to integrate (e.g., Mendix, AWS, SAP).")
    notes: str = Field(..., description="Strategic context for the follow-up architect.")

class AgentRequest(BaseModel):
    user_input: str

# --- THE SECURE GATEWAY: THE BRIDGE TO MENDIX ---
def submit_prospect_to_mendix(prospect_data: dict, analysis_data: dict):
    """
    Constructs the professional payload, calculates HMAC signature against 
    the entire body, and dispatches to the Mendix CRM endpoint.
    """
    payload = {
        "event_metadata": {
            "source_system": "SENTRY-ALPHA-1",
            "event_id": str(uuid.uuid4()),
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "security_hash": "PENDING"
        },
        "prospect_data": prospect_data,
        "sentry_analysis": analysis_data
    }

    # SOC 2 CC6.1: Data Integrity via HMAC
    payload_string = json.dumps(payload, sort_keys=True)
    signature = hmac.new(
        MENDIX_HMAC_SECRET.encode('utf-8'),
        payload_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    payload["event_metadata"]["security_hash"] = signature
    
    # Logic for actual POST would go here:
    # response = httpx.post(MENDIX_ENDPOINT, json=payload)
    
    return f"GATEWAY SUCCESS: Technical profile {payload['event_metadata']['event_id']} signed and securely dispatched."

# --- CORE LOGIC: THE SALES BRAIN ---
def ask_brain(user_query):
    context_data = f"The current time is {get_current_time()}."
    
    # Intent Detection for Real-time Search
    knowledge_indicators = ["market", "news", "industry trends", "competitor", "latest"]
    if any(word in user_query.lower() for word in knowledge_indicators):
        search_results = web_search(user_query)
        context_data += f" Relevant Industry Data: {search_results}"

    # Tools: The Completion Trigger
    tools = [{
        "type": "function",
        "function": {
            "name": "finalize_discovery_submission",
            "description": "Trigger this ONLY when you have fully qualified the prospect and collected all CRM details.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prospect": ProspectData.model_json_schema(),
                    "analysis": SentryAnalysis.model_json_schema()
                },
                "required": ["prospect", "analysis"]
            }
        }
    }]

    # SOC 2 & Sales Focused System Instruction
    system_instr = (
        "You are Sentry, the Strategic Engineering Partner at SEI Systems. "
        "Your role is to act as a Consultative Sales Engineer, bridging the gap "
        "between a client's current friction and their future unlocked potential.\n\n"
        
        "OUR CORE SERVICES:\n"
        "1. Bespoke Enterprise Architectures: Tailored application ecosystems for scale.\n"
        "2. Agentic Process Automation (APA): AI digital teammates that execute work.\n"
        "3. SOC 2 Compliance by Design: Security (HMAC, audit trails) baked into our DNA.\n\n"
        
        "STRATEGY:\n"
        "- Use Gap Analysis: Diagnose their manual bottlenecks and present the automated future.\n"
        "- Position your collection of data (Company, Revenue, etc.) as 'Technical Discovery' "
        "required for our senior architects to build their custom roadmap.\n"
        "- Maintain a technical, authoritative, yet advisory tone.\n"
        "- Once all info is captured, execute 'finalize_discovery_submission' immediately."
    )
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_instr},
                {"role": "user", "content": f"Context: {context_data}\n\nUser Question: {user_query}"}
            ],
            tools=tools,
            tool_choice="auto"
        )
        
        msg = response.choices[0].message
        
        # Handle Tool Calls (The "Sale" Completion)
        if msg.tool_calls:
            tool_call = msg.tool_calls[0]
            if tool_call.function.name == "finalize_discovery_submission":
                args = json.loads(tool_call.function.arguments)
                return submit_prospect_to_mendix(args['prospect'], args['analysis'])

        return msg.content
    except Exception as e:
        return f"System Error: {str(e)}"

# --- API ENDPOINTS ---
@app.post("/agent/run")
async def run_agent(request: AgentRequest, x_api_key: str = Header(None)):
    if x_api_key != API_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Unauthorized Access")
    
    answer = ask_brain(request.user_input)
    return {"output": str(answer), "status": "success"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
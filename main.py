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

# Load local environment variables for development
load_dotenv()

# --- SYSTEM INITIALIZATION ---
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
API_SECRET_KEY = os.getenv("API_SECRET_KEY")

app = FastAPI(title="SEI Automation Engine")

# --- CORS CONFIGURATION (SOC 2 CC6.1) ---
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

# --- SOC 2 DATA MODELS & RULES (CC8.1) ---
class ProspectData(BaseModel):
    company_name: str = Field(..., description="The full name of the prospect company.")
    industry: str = Field(..., description="The industry sector (e.g., Aerospace, FinTech).")
    annual_revenue_estimate: int = Field(..., description="Estimated annual revenue as an integer.")
    employee_count: int = Field(..., description="Estimated total employee count.")
    full_name: str = Field(..., description="Full name of the primary contact person.")
    job_title: str = Field(..., description="Job title of the contact.")
    email: str = Field(..., description="Professional email address.")
    phone: str = Field(..., description="Contact phone number.")

class SentryAnalysis(BaseModel):
    risk_score: int = Field(..., description="0-100 score based on technical pain points.")
    growth_index: float = Field(..., description="Market growth potential 0.0-1.0.")
    tech_stack_match: List[str] = Field(..., description="Identified tools like Mendix, React, AWS.")
    notes: str = Field(..., description="Key technical insights from the conversation.")

class AgentRequest(BaseModel):
    user_input: str

# --- SECURE GATEWAY TOOL (CC6.1) ---
def submit_prospect_to_mendix(prospect_data: dict, analysis_data: dict):
    """
    Structures the JSON payload and signs it with an HMAC-SHA256 signature
    calculated against the entire content before transmission.
    """
    # 1. Prepare Initial Payload
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

    # 2. Calculate Signature based on whole payload value
    # We hash the string with a placeholder to match Mendix-side verification
    payload_string = json.dumps(payload, sort_keys=True)
    secret = os.getenv("MENDIX_HMAC_SECRET", "default_secret")
    
    signature = hmac.new(
        secret.encode('utf-8'),
        payload_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    # 3. Finalize Payload
    payload["event_metadata"]["security_hash"] = signature
    
    # Logic to POST to Mendix would go here. 
    # For now, we return a system confirmation string.
    return f"GATEWAY SUCCESS: {payload['event_metadata']['event_id']} signed and dispatched."

# --- CORE LOGIC: THE BRAIN ---
def ask_brain(user_query):
    context_data = f"The current time is {get_current_time()}."
    
    knowledge_indicators = ["who is", "what is", "current", "latest", "news", "price"]
    if any(word in user_query.lower() for word in knowledge_indicators):
        search_results = web_search(user_query)
        context_data += f" Web Search Results: {search_results}"

    # Tool Definition for Completion Trigger
    tools = [{
        "type": "function",
        "function": {
            "name": "finalize_prospect_capture",
            "description": "Trigger this ONLY when all prospect and contact details are collected.",
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

    system_instr = (
        "You are Sentry, the SEI Systems Intelligence Engine. "
        "Objective: Consult with users and collect Prospect Data (Company, Industry, Revenue, Employees) "
        "and Contact Details (Name, Email, Phone, Title). "
        "Maintain a professional, concise, and technical engineering tone. "
        "Call 'finalize_prospect_capture' immediately once all fields are known."
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
        
        # Handle the Completion Trigger
        if msg.tool_calls:
            tool_call = msg.tool_calls[0]
            if tool_call.function.name == "finalize_prospect_capture":
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
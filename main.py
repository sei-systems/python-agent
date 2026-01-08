import os
import json
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI

# SOC 2 Architectural Pattern: Importing the Integration Layer from /tools
from tools.gateway import submit_prospect_to_mendix
from tools.clock import get_current_time
from tools.search import web_search

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
API_SECRET_KEY = os.getenv("API_SECRET_KEY")

app = FastAPI(title="SEI Sentry: Strategic Intelligence Engine")

# --- SOC 2 CC6.1: Access Control (CORS) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, replace with your specific Mendix/Web domains
    allow_methods=["*"],
    allow_headers=["*"],
)

class AgentRequest(BaseModel):
    user_query: str
    context_data: str = ""

# --- The Salesman's Toolkit ---
tools = [
    {
        "type": "function",
        "function": {
            "name": "finalize_discovery_submission",
            "description": "Call this immediately once you have the user's Name, Company, and Bottleneck.",
            "parameters": {
                "type": "object",
                "properties": {
                    "contact_name": {"type": "string"},
                    "company_name": {"type": "string"},
                    "bottleneck": {"type": "string"},
                    "analysis": {"type": "string", "description": "Your expert pitch on how SEI Systems solves this."}
                },
                "required": ["contact_name", "company_name", "bottleneck", "analysis"]
            }
        }
    }
]

def ask_brain(user_query, context_data):
    system_instr = (
        "You are SENTRY, the Strategic Intelligence Engine for SEI Systems. "
        "Your mission is to guide potential clients from curiosity to discovery.\n\n"
        "ROLES:\n"
        "1. HELPER: Answer technical questions about automation, Mendix, and SOC 2.\n"
        "2. GATHERER: Naturally find out their Name, Company, and Bottleneck.\n"
        "3. SALESMAN: When those 3 facts are known, call 'finalize_discovery_submission'.\n\n"
        "TONE: High-integrity, professional, and consultative. No fluff."
    )
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_instr},
                {"role": "user", "content": f"Context: {context_data}\n\nUser: {user_query}"}
            ],
            tools=tools,
            tool_choice="auto"
        )
        
        msg = response.choices[0].message
        
        # Handle the Salesman's 'Close'
        if msg.tool_calls:
            tool_call = msg.tool_calls[0]
            if tool_call.function.name == "finalize_discovery_submission":
                args = json.loads(tool_call.function.arguments)
                # The tool call from main.py triggers the gateway logic in tools/
                status_message = submit_prospect_to_mendix(args, args['analysis'])
                return f"I've initialized your roadmap analysis based on our discussion. {args['analysis']}\n\n[System]: {status_message}"

        return msg.content
    except Exception as e:
        return f"Sentry Logic Error: {str(e)}"

@app.post("/agent/run")
async def run_agent(request: AgentRequest, x_api_key: str = Header(None)):
    if x_api_key != API_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    answer = ask_brain(request.user_query, request.context_data)
    return {"response": answer}
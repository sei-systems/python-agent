import os
import json
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from openai import OpenAI

# Importing from your tools directory
from tools.gateway import submit_prospect_to_mendix
from tools.clock import get_current_time
from tools.search import web_search

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
API_SECRET_KEY = os.getenv("API_SECRET_KEY")

app = FastAPI(title="SEI Sentry: Strategic Intelligence Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# FIXED: Optional fields prevent the 422 Unprocessable Entity error from Mendix
class AgentRequest(BaseModel):
    user_query: str
    context_data: Optional[str] = ""

# The Salesman's Tool Definition
tools = [
    {
        "type": "function",
        "function": {
            "name": "finalize_discovery_submission",
            "description": "Call this once you have: Name, Company, Size, Tech Stack, and Bottleneck.",
            "parameters": {
                "type": "object",
                "properties": {
                    "contact_name": {"type": "string"},
                    "company_name": {"type": "string"},
                    "employee_count": {"type": "string"},
                    "tech_stack": {"type": "string"},
                    "bottleneck": {"type": "string"},
                    "analysis": {"type": "string", "description": "Sentry's expert pitch."}
                },
                "required": ["contact_name", "company_name", "bottleneck"]
            }
        }
    }
]

def ask_brain(user_query, context_data):
    system_instr = (
        "You are SENTRY, the Strategic Intelligence Engine for SEI Systems. "
        "1. HELPER: Answer technical questions about SOC 2 and automation.\n"
        "2. GATHERER: Collect Name, Company, Size, Tech Stack, and Bottleneck.\n"
        "3. SALESMAN: Call 'finalize_discovery_submission' to push the lead to Mendix.\n"
        "Tone: Professional, expert, consultative."
    )
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_instr},
                {"role": "user", "content": f"Context: {context_data}\n\nUser: {user_query}"}
            ],
            tools=tools
        )
        
        msg = response.choices[0].message
        if msg.tool_calls:
            args = json.loads(msg.tool_calls[0].function.arguments)
            # This calls the gateway in your tools folder
            return submit_prospect_to_mendix(args, args.get('analysis', ''))

        return msg.content
    except Exception as e:
        return f"Sentry System Error: {str(e)}"

@app.post("/agent/run")
async def run_agent(request: AgentRequest, x_api_key: str = Header(None)):
    if x_api_key != API_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Unauthorized Access")
    answer = ask_brain(request.user_query, request.context_data)
    return {"response": answer}
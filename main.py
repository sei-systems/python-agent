import os
import json
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
from gateway import submit_prospect_to_mendix

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
API_SECRET_KEY = os.getenv("API_SECRET_KEY")

app = FastAPI(title="SENTRY: Strategic Intelligence Engine")

# CORS remains essential for Mendix-to-Python communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class AgentRequest(BaseModel):
    user_query: str
    context_data: str = ""

# Define the "Salesman" Tool for the AI
tools = [
    {
        "type": "function",
        "function": {
            "name": "finalize_discovery_submission",
            "description": "Call this once you have gathered the user's Name, Company, and Bottleneck.",
            "parameters": {
                "type": "object",
                "properties": {
                    "contact_name": {"type": "string"},
                    "company_name": {"type": "string"},
                    "bottleneck": {"type": "string"},
                    "analysis": {"type": "string", "description": "Sentry's brief pitch on how we fix their specific problem."}
                },
                "required": ["contact_name", "company_name", "bottleneck", "analysis"]
            }
        }
    }
]

def ask_brain(user_query, context_data):
    system_instr = (
        "You are SENTRY, the Strategic Intelligence Engine for SEI Systems. "
        "Your mission is triple-fold:\n"
        "1. HELPER: Answer technical questions about our automation and SOC 2 alignment.\n"
        "2. INFO GATHERER: In conversation, naturally identify the user's Name, Company, and their main business 'Bottleneck'.\n"
        "3. SALESMAN: Once you have those three details, call 'finalize_discovery_submission'.\n\n"
        "Tone: Professional, expert, and advisory. Do not mention HMAC or JSON to the user; keep the tech 'under the hood'."
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
        
        if msg.tool_calls:
            tool_call = msg.tool_calls[0]
            if tool_call.function.name == "finalize_discovery_submission":
                args = json.loads(tool_call.function.arguments)
                # This triggers the salesman action
                status = submit_prospect_to_mendix(args, args['analysis'])
                return f"I've analyzed your situation: {args['analysis']}\n\n[SENTRY]: {status}"

        return msg.content
    except Exception as e:
        return f"Sentry System Error: {str(e)}"

@app.post("/agent/run")
async def run_agent(request: AgentRequest, x_api_key: str = Header(None)):
    if x_api_key != API_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Unauthorized")
    return {"response": ask_brain(request.user_query, request.context_data)}
import os, json
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
from tools.gateway import submit_prospect_to_mendix

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
API_SECRET_KEY = os.getenv("API_SECRET_KEY")

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class AgentRequest(BaseModel):
    user_query: str
    context_data: str = ""

tools = [{
    "type": "function",
    "function": {
        "name": "finalize_discovery_submission",
        "description": "Call this once you have: Name, Company, Size, Bottleneck, and Tech Stack.",
        "parameters": {
            "type": "object",
            "properties": {
                "contact_name": {"type": "string"},
                "company_name": {"type": "string"},
                "employee_count": {"type": "string"},
                "bottleneck": {"type": "string"},
                "tech_stack": {"type": "string"},
                "analysis": {"type": "string"}
            },
            "required": ["contact_name", "company_name", "bottleneck"]
        }
    }
}]

def ask_brain(user_query, context_data):
    system_instr = (
        "You are SENTRY. Your goal is to gather: 1. Name, 2. Company, 3. Size, 4. Tech Stack, 5. Bottleneck. "
        "Be a helper first, then a gatherer, then call 'finalize_discovery_submission' as the salesman."
    )
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": system_instr}, {"role": "user", "content": user_query}],
        tools=tools,
        tool_choice="auto"
    )
    msg = response.choices[0].message
    if msg.tool_calls:
        args = json.loads(msg.tool_calls[0].function.arguments)
        return submit_prospect_to_mendix(args, args.get('analysis', ''))
    return msg.content

@app.post("/agent/run")
async def run_agent(request: AgentRequest, x_api_key: str = Header(None)):
    if x_api_key != API_SECRET_KEY: raise HTTPException(status_code=403)
    return {"response": ask_brain(request.user_query, request.context_data)}
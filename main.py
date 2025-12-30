import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
from tools.clock import get_current_time
from tools.search import web_search

# Load local environment variables for development
load_dotenv()

# --- SYSTEM INITIALIZATION ---
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
API_SECRET_KEY = os.getenv("API_SECRET_KEY")

app = FastAPI(title="SEI Automation Engine")

# --- STEP 1.2: CORS CONFIGURATION ---
# Permitting high-performance cross-origin data streams between our specialized domains.
origins = [
    "https://www.seisystems.co",   # Main Portfolio
    "https://seisystems.co",       # Apex Domain
    "https://labs.seisystems.co",  # Mendix Interactive Labs
    "http://localhost:8080",       # Local Mendix Testing
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AgentRequest(BaseModel):
    user_input: str

# --- CORE LOGIC: THE BRAIN ---
def ask_brain(user_query):
    context_data = f"The current time is {get_current_time()}."
    
    # Intelligent Classifier: Only trigger search when external context is required.
    knowledge_indicators = ["who is", "what is", "current", "latest", "news", "price"]
    
    if any(word in user_query.lower() for word in knowledge_indicators):
        search_results = web_search(user_query)
        context_data += f" Web Search Results: {search_results}"

    system_instr = (
        "You are the SEI Systems Intelligence Engine. "
        "Your focus is on providing efficient, accurate automation insights. "
        "Be concise, technical, and professional."
    )
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_instr},
                {"role": "user", "content": f"Context: {context_data}\n\nUser Question: {user_query}"}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"System Error: {str(e)}"

# --- API ENDPOINTS ---
@app.post("/agent/run")
async def run_agent(request: AgentRequest, x_api_key: str = Header(None)):
    if x_api_key != API_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Unauthorized Access")
    
    answer = ask_brain(request.user_input)
    return {"output": str(answer), "status": "success"}

# --- RENDER PORT BINDING ---
# Ensures the application binds to the dynamic port assigned by the cloud environment.
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
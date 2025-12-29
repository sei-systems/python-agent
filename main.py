import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from openai import OpenAI
from tools.clock import get_current_time
from tools.search import web_search

load_dotenv()

# Initialize OpenAI Client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
API_SECRET_KEY = os.getenv("API_SECRET_KEY")

app = FastAPI()

class AgentRequest(BaseModel):
    user_input: str

def ask_brain(user_query):
    context_data = ""
    
    # 1. Proactive Time Check (Always good for context)
    context_data += f" The current time is {get_current_time()}."
    
    # 2. Smart Search Trigger
    # Instead of keywords, we look for 'current', 'news', 'menu', 'weather', or general knowledge
    # SOC2: This ensures we only use external egress when necessary.
    general_knowledge_indicators = ["who is", "what is", "where is", "how many", "current", "latest", "price", "menu"]
    
    if any(word in user_query.lower() for word in general_knowledge_indicators):
        print(f"DEBUG: Internal Classifier triggered Search for: {user_query}")
        search_results = web_search(user_query)
        context_data += f" Web Search Results: {search_results}"

    # 3. Final SOC2 System Prompt
    system_instr = (
        "You are an AI Agent for SEI Systems. "
        "Your responses must be professional, accurate, and based on the provided context. "
        "If you do not have the answer in the context or your training data, state that you cannot find the information."
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
        print(f"CRITICAL ERROR: {e}")
        return "I'm sorry, I'm having trouble connecting to my knowledge base right now."

@app.post("/agent/run")
async def run_agent(request: AgentRequest, x_api_key: str = Header(None)):
    if x_api_key != API_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    
    try:
        answer = ask_brain(request.user_input)
        
        # SOC2 Debugging: Always log what we are sending
        print(f"DEBUG: Sending to Mendix: {answer}", flush=True) 
        
        # WE MATCH THE MENDIX KEYS HERE:
        return {
            "output": str(answer),
            "status": "success"
        }
        
    except Exception as e:
        print(f"CRITICAL ERROR: {str(e)}", flush=True)
        # Match Mendix error pattern if possible
        return {
            "output": f"Error: {str(e)}",
            "status": "error"
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
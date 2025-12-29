import os
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, AgentType, load_tools

# 1. Load Secrets
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
API_SECRET_KEY = os.getenv("API_SECRET_KEY") # Matches your Mendix Constant

app = FastAPI()

# 2. Define the Data Schema (Matches your Mendix Export/Import)
class AgentRequest(BaseModel):
    user_input: str

# 3. Initialize the "Brain"
llm = ChatOpenAI(model="gpt-4-turbo", temperature=0)
# We can add tools like 'serpapi' for web search or 'wikipedia' later
tools = load_tools([], llm=llm) 

agent = initialize_agent(
    tools, 
    llm, 
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, 
    verbose=True # This lets you see the "Thinking" in your VS Code terminal
)

@app.post("/agent/run")
async def run_agent(request: AgentRequest, x_api_key: str = Header(None)):
    # Security: Validate the Mendix Shared Secret
    if x_api_key != API_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Unauthorized Access")

    try:
        # The Agent "thinks" and returns a result
        response = agent.run(request.user_input)
        return {"output": response, "status": "success"}
    except Exception as e:
        return {"output": str(e), "status": "error"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
from fastapi import FastAPI, Depends, Request, Response, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi_clerk_auth import ClerkConfig, ClerkHTTPBearer
from supabase import create_client, Client
from .config import get_settings
from pydantic import BaseModel
from typing import Optional
import asyncio
import httpx

settings = get_settings()

# Initialize Supabase
supabase: Client = create_client(
    settings.supabase_url,
    settings.supabase_anon_key
)

# Configure Clerk Auth
clerk_config = ClerkConfig(jwks_url=settings.clerk_jwks_url)
clerk_auth = ClerkHTTPBearer(config=clerk_config, add_state=True)

app = FastAPI(title="ElevenAgents API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.environment == "development" else ["https://nyu-buildathon.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper function to get user from request
def get_user(request: Request) -> dict:
    credentials = request.state.credentials
    return {
        "user_id": credentials.decoded.get("sub"),
        "email": credentials.decoded.get("email")
    }

# ==================== PUBLIC AGENT ROUTES ====================

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/api/agent/signed-url")
async def get_agent_signed_url():
    """
    Generates a signed URL for the frontend to securely connect 
    to the ElevenLabs Conversational AI agent.
    """
    agent_id = settings.elevenlabs_agent_id
    api_key = settings.elevenlabs_api_key
    
    if not agent_id or not api_key:
        return {"error": "Agent not configured"}
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://api.elevenlabs.io/v1/convai/conversation/get_signed_url?agent_id={agent_id}",
                headers={"xi-api-key": api_key}
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        print(f"Error getting signed URL: {e}")
        return {"error": str(e)}

@app.post("/api/agent/webhook")
async def agent_webhook(request: Request):
    """
    Post-conversation webhook for ElevenLabs.
    Configure this in ElevenLabs Agent -> Advanced -> Webhooks.
    """
    data = await request.json()
    # Logic to save transcript/summary to Supabase
    print(f"Received ElevenLabs Webhook: {data.get('type')}")
    return {"status": "received"}

@app.post("/api/agent/tools")
async def agent_tools(request: Request):
    """
    Server-side tools handler.
    Configure this in ElevenLabs Agent -> Tools.
    """
    data = await request.json()
    tool_name = data.get("tool_name")
    arguments = data.get("arguments", {})
    
    # Custom logic based on tool_name
    if tool_name == "get_user_info":
        return {"name": "Buildathon User", "status": "active"}
    
    return {"status": "success", "message": f"Tool {tool_name} executed"}

# ==================== PROTECTED ROUTES (Clerk Auth) ====================

authenticated_router = APIRouter(dependencies=[Depends(clerk_auth)])

class AgentRequest(BaseModel):
    query: str
    context: Optional[dict] = None

class AgentResponse(BaseModel):
    result: str
    user_id: str
    steps: list[str]

@authenticated_router.get("/api/profile")
def get_profile(request: Request):
    user = get_user(request)
    return user

@authenticated_router.post("/api/agent/run", response_model=AgentResponse)
async def run_agent(req: AgentRequest, request: Request):
    user = get_user(request)
    return AgentResponse(
        result="Direct Agent Action Triggered",
        user_id=user["user_id"],
        steps=["Research", "Plan", "Execute"]
    )

app.include_router(authenticated_router)

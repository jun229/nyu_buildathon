from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi_clerk_auth import ClerkConfig, ClerkHTTPBearer
from supabase import create_client, Client
from .config import get_settings
from pydantic import BaseModel
from typing import Optional
import asyncio

settings = get_settings()

# Initialize Supabase
supabase: Client = create_client(
    settings.supabase_url,
    settings.supabase_anon_key
)

# Configure Clerk Auth
clerk_config = ClerkConfig(jwks_url=settings.clerk_jwks_url)
clerk_auth = ClerkHTTPBearer(config=clerk_config, add_state=True)

DEV_USER = {"sub": "dev-user-id", "email": "dev@localhost"}

async def auth_dependency(request: Request):
    """Skip Clerk auth in development mode."""
    if settings.environment == "development":
        request.state.credentials = type("_Creds", (), {"decoded": DEV_USER})()
        return
    return await clerk_auth(request)

# Create app with global auth dependency
app = FastAPI(
    title="Buildathon API",
    dependencies=[Depends(auth_dependency)]  # ALL ROUTES PROTECTED
)

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

# ==================== MODELS ====================

class AgentRequest(BaseModel):
    query: str
    context: Optional[dict] = None

class AgentResponse(BaseModel):
    result: str
    user_id: str
    steps: list[str]

# ==================== ROUTES ====================

@app.get("/health")
def health(request: Request):
    """Health check - protected"""
    user = get_user(request)
    return {
        "status": "healthy",
        "user_id": user["user_id"]
    }

@app.post("/api/agent/run", response_model=AgentResponse)
async def run_agent(
    req: AgentRequest,
    request: Request
):
    """Run agent orchestration - 1-2 min processing"""
    user = get_user(request)
    user_id = user["user_id"]
    
    # Log to Supabase (optional)
    # supabase.table("agent_runs").insert({
    #     "user_id": user_id,
    #     "query": req.query,
    #     "status": "running"
    # }).execute()
    
    # TODO: Your actual agent orchestration logic
    await asyncio.sleep(2)  # Simulate processing
    
    return AgentResponse(
        result="Agent completed successfully",
        user_id=user_id,
        steps=["Step 1", "Step 2", "Step 3"]
    )

@app.get("/api/agent/history")
def get_history(request: Request, limit: int = 10):
    """Get user's agent history"""
    user = get_user(request)
    
    # TODO: Query Supabase
    # data = supabase.table("agent_runs")\
    #     .select("*")\
    #     .eq("user_id", user["user_id"])\
    #     .limit(limit)\
    #     .execute()
    
    return {
        "user_id": user["user_id"],
        "runs": []
    }

@app.get("/api/profile")
def get_profile(request: Request):
    """Get current user profile"""
    user = get_user(request)
    return user
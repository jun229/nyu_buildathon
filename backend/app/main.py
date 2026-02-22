from fastapi import FastAPI, Depends, Request, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi_clerk_auth import ClerkConfig, ClerkHTTPBearer
from supabase import create_client, Client
from .config import get_settings
from pydantic import BaseModel
from typing import Optional
import asyncio
import httpx
import time
import uuid

settings = get_settings()

# Anon client for user-scoped queries
supabase: Client = create_client(
    settings.supabase_url,
    settings.supabase_anon_key
)

# Admin client for storage uploads (bypasses RLS)
supabase_admin: Client = create_client(
    settings.supabase_url,
    settings.supabase_service_role_key
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

app = FastAPI(
    title="Buildathon API",
    dependencies=[Depends(auth_dependency)]
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.environment == "development" else ["https://nyu-buildathon.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

class PlatformResult(BaseModel):
    name: str
    avg_price: float
    demand: str  # "high" | "medium" | "low"
    time_to_sell_days: int

class LocalStore(BaseModel):
    name: str
    address: str
    phone: str
    distance_miles: float
    specialty: str

class AnalyzeResponse(BaseModel):
    image_url: str
    item_name: str
    estimated_price_range: dict  # { min, max, currency }
    best_platform: str
    platforms: list[PlatformResult]
    local_stores: list[LocalStore]
    condition_tips: list[str]
    confidence: float
    processing_time_ms: int

# ==================== ROUTES ====================

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/api/profile")
def get_profile(request: Request):
    return get_user(request)

@app.get("/api/agent/history")
def get_history(request: Request, limit: int = 10):
    user = get_user(request)
    return {
        "user_id": user["user_id"],
        "runs": []
    }

# ==================== ELEVENLABS ROUTES ====================

@app.get("/api/agent/signed-url")
async def get_agent_signed_url():
    """Generate a signed URL for the frontend to connect to ElevenLabs."""
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
    Configure in ElevenLabs Agent -> Advanced -> Webhooks.
    """
    data = await request.json()
    print(f"Received ElevenLabs Webhook: {data.get('type')}")
    return {"status": "received"}

@app.post("/api/agent/tools")
async def agent_tools(request: Request):
    """
    Server-side tools handler.
    Configure in ElevenLabs Agent -> Tools.
    """
    data = await request.json()
    tool_name = data.get("tool_name")
    arguments = data.get("arguments", {})

    if tool_name == "get_user_info":
        return {"name": "Buildathon User", "status": "active"}

    return {"status": "success", "message": f"Tool {tool_name} executed"}

@app.post("/api/agent/run", response_model=AgentResponse)
async def run_agent(req: AgentRequest, request: Request):
    user = get_user(request)
    return AgentResponse(
        result="Direct Agent Action Triggered",
        user_id=user["user_id"],
        steps=["Research", "Plan", "Execute"]
    )

# ==================== ANALYZE ROUTE ====================

@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze_product(
    request: Request,
    file: UploadFile = File(...),
):
    """
    Accept image file via multipart upload.
    1. Upload to Supabase Storage (service role — bypasses RLS)
    2. Run AI pipeline (stub — replace TODO block with real logic)
    3. Return structured pricing result
    """
    start = time.time()
    user = get_user(request)
    user_id = user["user_id"]

    file_bytes = await file.read()

    ext = (file.filename or "image.jpg").rsplit(".", 1)[-1].lower()
    storage_path = f"{user_id}/{int(time.time() * 1000)}-{uuid.uuid4()}.{ext}"

    supabase_admin.storage.from_("product-images").upload(
        path=storage_path,
        file=file_bytes,
        file_options={"content-type": file.content_type or "image/jpeg"},
    )

    signed = supabase_admin.storage.from_("product-images").create_signed_url(
        storage_path, 3600
    )
    image_url = signed.get("signedURL") or signed.get("signedUrl") or ""

    # TODO: Replace with real AI pipeline using file_bytes:
    # 1. Run vision model to identify item
    # 2. Query marketplace APIs (eBay, Depop, Mercari) for price data
    # 3. Log run to Supabase analysis_runs table
    await asyncio.sleep(1.5)  # simulate processing

    return AnalyzeResponse(
        image_url=image_url,
        item_name="Vintage Denim Jacket",
        estimated_price_range={"min": 45.0, "max": 95.0, "currency": "USD"},
        best_platform="eBay",
        platforms=[
            PlatformResult(name="eBay", avg_price=72.0, demand="high", time_to_sell_days=7),
            PlatformResult(name="Depop", avg_price=68.0, demand="high", time_to_sell_days=5),
            PlatformResult(name="Mercari", avg_price=55.0, demand="medium", time_to_sell_days=14),
            PlatformResult(name="Facebook Marketplace", avg_price=40.0, demand="low", time_to_sell_days=21),
        ],
        local_stores=[
            LocalStore(name="Brooklyn Vintage Co.", address="234 Bedford Ave, Brooklyn, NY 11211", phone="(718) 555-0142", distance_miles=0.8, specialty="Vintage Clothing"),
            LocalStore(name="Re-Up Resale", address="89 Graham Ave, Brooklyn, NY 11206", phone="(718) 555-0289", distance_miles=1.4, specialty="Streetwear & Denim"),
            LocalStore(name="Second Stitch", address="412 Myrtle Ave, Brooklyn, NY 11205", phone="(718) 555-0374", distance_miles=2.1, specialty="General Resale"),
            LocalStore(name="The Good Thrift", address="56 Wilson Ave, Brooklyn, NY 11237", phone="(718) 555-0461", distance_miles=3.3, specialty="Vintage & Thrift"),
        ],
        condition_tips=[
            "Clean any visible stains before listing",
            "Photograph the label and all hardware clearly",
            "Measure chest, length, and sleeve for the description",
        ],
        confidence=0.82,
        processing_time_ms=int((time.time() - start) * 1000),
    )

from fastapi import FastAPI, Depends, File, UploadFile, Form, HTTPException, Query
import random
from fastapi.middleware.cors import CORSMiddleware
from fastapi_clerk_auth import ClerkConfig, ClerkHTTPBearer
from supabase import create_client, Client
from .config import get_settings
from pydantic import BaseModel
from typing import Optional
import asyncio
import time
import uuid
import os
import sys
import json
import tempfile

settings = get_settings()

# ---------------------------------------------------------------------------
# Add the agents directory to the path so we can import agent.py directly
# ---------------------------------------------------------------------------
_APP_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(os.path.dirname(_APP_DIR))
_AGENTS_DIR = os.path.join(_PROJECT_DIR, "agents")
if _AGENTS_DIR not in sys.path:
    sys.path.insert(0, _AGENTS_DIR)

import agent as appraisal_agent  # noqa: E402  (import after sys.path mutation)

# ---------------------------------------------------------------------------
# Supabase clients — factory functions to avoid shared-client concurrency issues
# ---------------------------------------------------------------------------
def get_supabase_admin() -> Client:
    return create_client(settings.supabase_url, settings.supabase_service_role_key)

# ---------------------------------------------------------------------------
# Clerk auth
# ---------------------------------------------------------------------------
clerk_config = ClerkConfig(jwks_url=settings.clerk_jwks_url)
clerk_auth = ClerkHTTPBearer(config=clerk_config, add_state=False)

app = FastAPI(title="Buildathon API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://nyu-buildathon.vercel.app",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_user(credentials=Depends(clerk_auth)) -> dict:
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
    demand: str                          # "high" | "medium" | "low"
    time_to_sell_days: Optional[int] = None
    sell_through_rate: Optional[str] = None  # "high" | "medium" | "low"

class LocalStore(BaseModel):
    name: str
    address: str
    phone: str
    distance_miles: Optional[float] = None  # not returned by agent; reserved for future geocoding
    specialty: str                           # derived from shop_type
    rating: Optional[float] = None
    priority: Optional[int] = None
    reason: Optional[str] = None
    shop_type: Optional[str] = None         # "pawn" | "specialty" | "buyer"

class NegotiationStrategy(BaseModel):
    opening_price: float
    target_price: float
    walk_away_price: float
    opening_script: str
    counter_script: str
    accept_script: str
    walk_away_script: str

class AnalyzeResponse(BaseModel):
    analysis_id: str = ""                # uuid of the persisted analyses row
    image_url: str
    item_name: str
    item_description: str
    condition: str                       # "like_new" | "excellent" | "good" | "fair" | "poor"
    estimated_price_range: dict          # { low, fair, high, currency }
    market_context: str
    best_platform: str
    platforms: list[PlatformResult]
    local_stores: list[LocalStore]
    negotiation_strategy: Optional[NegotiationStrategy] = None
    condition_tips: list[str]
    confidence: float                    # 0–1 based on swarm success rate
    processing_time_ms: int


# ==================== HELPERS ====================

def _normalize_demand(raw: str) -> str:
    mapping = {
        "very_high": "high", "high": "high",
        "medium": "medium",
        "low": "low", "very_low": "low",
    }
    return mapping.get((raw or "").lower(), "medium")


def _map_agent_state_to_response(
    state: dict,
    image_url: str,
    start_time: float,
) -> AnalyzeResponse:
    """Convert LangGraph state returned by agent.run() into AnalyzeResponse."""
    payload = state.get("final_payload", {})
    swarm: list[dict] = state.get("swarm_results", [])

    # Parse the vision condition blob (stored as JSON string in state)
    condition_raw = state.get("condition_details", "{}")
    try:
        condition_data = json.loads(condition_raw) if isinstance(condition_raw, str) else condition_raw
    except (json.JSONDecodeError, TypeError):
        condition_data = {}

    # ---- price range ----
    mv = payload.get("estimated_market_value", {})
    estimated_price_range = {
        "low": mv.get("low", 0),
        "fair": mv.get("fair", 0),
        "high": mv.get("high", 0),
        "currency": "USD",
    }

    # ---- index swarm workers by name ----
    swarm_by_worker = {
        r["worker"]: r.get("result", {})
        for r in swarm
        if "worker" in r and "result" in r
    }

    # ---- demand level (used as fallback for platforms without their own demand) ----
    demand_data = swarm_by_worker.get("market_demand_analyst", {})
    overall_demand = demand_data.get("demand_level", "medium")

    # ---- platform results ----
    platforms: list[PlatformResult] = []

    online_data = swarm_by_worker.get("online_marketplace_analyst", {})
    for p in online_data.get("platforms", []):
        price = p.get("estimated_sold_price") or p.get("listing_price") or 0
        platforms.append(PlatformResult(
            name=p.get("name", ""),
            avg_price=float(price),
            demand=_normalize_demand(p.get("sell_through_rate", overall_demand)),
            sell_through_rate=p.get("sell_through_rate"),
        ))

    local_data = swarm_by_worker.get("local_marketplace_analyst", {})
    for p in local_data.get("platforms", []):
        platforms.append(PlatformResult(
            name=p.get("name", ""),
            avg_price=float(p.get("estimated_price") or 0),
            demand=_normalize_demand(overall_demand),
            time_to_sell_days=p.get("typical_days_to_sell"),
        ))

    best_platform = (
        max(platforms, key=lambda p: p.avg_price).name if platforms else "eBay"
    )

    # ---- condition tips from condition-impact analyst deductions ----
    condition_tips: list[str] = []
    cond_impact = swarm_by_worker.get("condition_impact_analyst", {})
    for d in cond_impact.get("deductions", []):
        factor = (d.get("factor") or "").strip()
        if factor:
            condition_tips.append(f"Address: {factor}")

    # Fallback: use the condition_details sentence from vision
    if not condition_tips:
        detail = condition_data.get("condition_details", "")
        if detail:
            condition_tips = [detail]

    # ---- local stores ----
    _shop_type_label = {
        "pawn": "Pawn Shop",
        "specialty": "Specialty Store",
        "buyer": "Used Goods Buyer",
    }
    local_stores: list[LocalStore] = []
    for s in payload.get("target_shops", []):
        shop_type = s.get("shop_type", "")
        local_stores.append(LocalStore(
            name=s.get("name", ""),
            address=s.get("address", ""),
            phone=s.get("phone", ""),
            specialty=_shop_type_label.get(shop_type, shop_type.replace("_", " ").title()),
            rating=s.get("rating"),
            priority=s.get("priority"),
            reason=s.get("reason"),
            shop_type=shop_type,
        ))

    # ---- negotiation strategy ----
    neg = payload.get("negotiation_strategy")
    negotiation_strategy: Optional[NegotiationStrategy] = None
    if neg:
        negotiation_strategy = NegotiationStrategy(
            opening_price=float(neg.get("opening_price") or 0),
            target_price=float(neg.get("target_price") or 0),
            walk_away_price=float(neg.get("walk_away_price") or 0),
            opening_script=neg.get("opening_script", ""),
            counter_script=neg.get("counter_script", ""),
            accept_script=neg.get("accept_script", ""),
            walk_away_script=neg.get("walk_away_script", ""),
        )

    # ---- confidence: fraction of swarm workers that parsed cleanly ----
    successful = sum(
        1 for r in swarm
        if "result" in r and not r.get("result", {}).get("parse_error")
    )
    confidence = round(successful / max(len(swarm), 1), 2)

    return AnalyzeResponse(
        image_url=image_url,
        item_name=payload.get("item_name") or state.get("identified_item", "Unknown Item"),
        item_description=payload.get("item_description", ""),
        condition=condition_data.get("condition_grade", "unknown"),
        estimated_price_range=estimated_price_range,
        market_context=payload.get("market_context", ""),
        best_platform=best_platform,
        platforms=platforms,
        local_stores=local_stores,
        negotiation_strategy=negotiation_strategy,
        condition_tips=condition_tips,
        confidence=confidence,
        processing_time_ms=int((time.time() - start_time) * 1000),
    )


# ==================== ROUTES ====================

@app.get("/health")
def health(user: dict = Depends(get_user)):
    return {"status": "healthy", "user_id": user["user_id"]}


@app.post("/api/agent/run", response_model=AgentResponse)
async def run_agent(req: AgentRequest, user: dict = Depends(get_user)):
    await asyncio.sleep(2)
    return AgentResponse(
        result="Agent completed successfully",
        user_id=user["user_id"],
        steps=["Step 1", "Step 2", "Step 3"]
    )


@app.get("/api/agent/history")
def get_history(user: dict = Depends(get_user)):
    return {"user_id": user["user_id"], "runs": []}


@app.get("/api/profile")
def get_profile(user: dict = Depends(get_user)):
    return user


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze_product(
    file: UploadFile = File(...),
    ll: str = Form(default="@40.7009973,-73.994778"),
    user: dict = Depends(get_user),
):
    """
    Accept an image + GPS coordinates (ll), run the full appraisal pipeline,
    and return structured pricing + shop data.

    Form fields:
      file  — image file (JPEG / PNG / WebP / GIF)
      ll    — GPS coordinates as "@latitude,longitude"
               e.g. "@40.7009973,-73.994778"
               A 10-mile search radius is applied automatically.
    """
    start = time.time()
    user_id = user["user_id"]
    db = get_supabase_admin()

    file_bytes = await file.read()

    # ---- upload original image to Supabase Storage ----
    ext = (file.filename or "image.jpg").rsplit(".", 1)[-1].lower()
    storage_path = f"{user_id}/{int(time.time() * 1000)}-{uuid.uuid4()}.{ext}"

    db.storage.from_("product-images").upload(
        path=storage_path,
        file=file_bytes,
        file_options={"content-type": file.content_type or "image/jpeg"},
    )

    signed = db.storage.from_("product-images").create_signed_url(storage_path, 3600)
    image_url = signed.get("signedURL") or signed.get("signedUrl") or ""

    # ---- write image to a temp file for agent.py (expects a path) ----
    tmp_path: Optional[str] = None
    try:
        with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        # Run the blocking agent pipeline in a thread so we don't block the event loop
        try:
            state = await asyncio.to_thread(appraisal_agent.run, tmp_path, ll)
        except SystemExit as exc:
            raise HTTPException(status_code=500, detail=f"Agent pipeline failed (exit {exc.code})")

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    response = _map_agent_state_to_response(state, image_url, start)

    # ---- persist analysis to Supabase (fresh client, post-thread) ----
    try:
        neg = response.negotiation_strategy
        insert_res = get_supabase_admin().table("analyses").insert({
            "user_id": user_id,
            "image_url": response.image_url,
            "item_name": response.item_name,
            "item_description": response.item_description,
            "condition": response.condition,
            "estimated_price_range": response.estimated_price_range,
            "market_context": response.market_context,
            "best_platform": response.best_platform,
            "platforms": [p.model_dump() for p in response.platforms],
            "local_stores": [s.model_dump() for s in response.local_stores],
            "negotiation_strategy": neg.model_dump() if neg else None,
            "condition_tips": response.condition_tips,
            "confidence": response.confidence,
            "processing_time_ms": response.processing_time_ms,
        }).execute()
        response.analysis_id = insert_res.data[0]["id"]
    except Exception as e:
        print(f"[warn] Failed to persist analysis: {e}")

    return response


# ==================== NEGOTIATION MODELS ====================

class NegotiateRequest(BaseModel):
    analysis_id: str

class NegotiateResponse(BaseModel):
    job_id: str
    status: str

class OfferResult(BaseModel):
    id: str
    store_name: str
    store_address: str
    store_phone: str
    store_specialty: str
    accepted: bool
    agreed_price: Optional[float]
    call_summary: Optional[str]

class OffersResponse(BaseModel):
    job_id: str
    status: str
    item_name: str
    image_url: str
    offers: list[OfferResult]


# ==================== NEGOTIATION HELPERS ====================

ELEVENLABS_AGENT_ID = "hardcoded_agent_id_placeholder"
ELEVENLABS_API_KEY = "hardcoded_key_placeholder"

_MOCK_SUMMARIES = [
    "Store was interested and agreed to the price after a brief negotiation.",
    "Owner reviewed the item details and confirmed they're ready to buy at the agreed price.",
    "Quick call — they said it fits their current inventory needs and accepted the offer.",
]

async def _run_negotiation_job(job_id: str, stores: list[dict], neg_strategy: Optional[dict]) -> None:
    """Mock ElevenLabs call per store. Replace inner logic with real API call later."""
    db = get_supabase_admin()
    db.table("negotiation_jobs").update({"status": "in_progress"}).eq("id", job_id).execute()

    walk_away = float((neg_strategy or {}).get("walk_away_price") or 50)
    target = float((neg_strategy or {}).get("target_price") or 100)

    for i, store in enumerate(stores):
        await asyncio.sleep(1)  # simulate call duration
        accepted = (i % 2 == 0)  # alternate accepted/rejected for mock
        agreed_price = round(random.uniform(walk_away, target), 2) if accepted else None
        summary = random.choice(_MOCK_SUMMARIES) if accepted else None

        get_supabase_admin().table("store_offers").update({
            "accepted": accepted,
            "agreed_price": agreed_price,
            "call_summary": summary,
        }).eq("job_id", job_id).eq("store_name", store.get("name", "")).execute()

    get_supabase_admin().table("negotiation_jobs").update({"status": "done"}).eq("id", job_id).execute()


# ==================== NEGOTIATION ROUTES ====================

@app.post("/api/negotiate", response_model=NegotiateResponse)
async def negotiate(req: NegotiateRequest, user: dict = Depends(get_user)):
    user_id = user["user_id"]
    db = get_supabase_admin()

    # Fetch analysis row (verify ownership)
    analysis_res = db.table("analyses").select("*").eq("id", req.analysis_id).eq("user_id", user_id).execute()
    if not analysis_res.data:
        raise HTTPException(status_code=404, detail="Analysis not found")
    analysis = analysis_res.data[0]

    stores: list[dict] = analysis.get("local_stores") or []
    neg_strategy: Optional[dict] = analysis.get("negotiation_strategy")

    # Create job row
    job_res = db.table("negotiation_jobs").insert({
        "user_id": user_id,
        "analysis_id": req.analysis_id,
        "status": "pending",
    }).execute()
    job_id = job_res.data[0]["id"]

    # Seed one store_offers row per store
    if stores:
        db.table("store_offers").insert([
            {
                "job_id": job_id,
                "store_name": s.get("name", ""),
                "store_address": s.get("address", ""),
                "store_phone": s.get("phone", ""),
                "store_specialty": s.get("specialty", ""),
                "accepted": False,
            }
            for s in stores
        ]).execute()

    asyncio.create_task(_run_negotiation_job(job_id, stores, neg_strategy))

    return NegotiateResponse(job_id=job_id, status="pending")


@app.get("/api/offers", response_model=OffersResponse)
async def get_offers(job_id: str = Query(...), user: dict = Depends(get_user)):
    user_id = user["user_id"]
    db = get_supabase_admin()

    job_res = db.table("negotiation_jobs").select("*").eq("id", job_id).eq("user_id", user_id).execute()
    if not job_res.data:
        raise HTTPException(status_code=404, detail="Job not found")
    job = job_res.data[0]

    analysis_res = db.table("analyses").select("item_name, image_url").eq("id", job["analysis_id"]).execute()
    analysis = analysis_res.data[0] if analysis_res.data else {}

    offers_res = db.table("store_offers").select("*").eq("job_id", job_id).execute()
    offers = [
        OfferResult(
            id=o["id"],
            store_name=o.get("store_name", ""),
            store_address=o.get("store_address", ""),
            store_phone=o.get("store_phone", ""),
            store_specialty=o.get("store_specialty", ""),
            accepted=o.get("accepted", False),
            agreed_price=o.get("agreed_price"),
            call_summary=o.get("call_summary"),
        )
        for o in (offers_res.data or [])
    ]

    return OffersResponse(
        job_id=job_id,
        status=job["status"],
        item_name=analysis.get("item_name", ""),
        image_url=analysis.get("image_url", ""),
        offers=offers,
    )

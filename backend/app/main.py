from fastapi import FastAPI, Depends, Request, File, UploadFile, Form, HTTPException, Query
import random
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


# ---- Calling models ----

class StoreCallTarget(BaseModel):
    id: str
    name: str
    phone_number: str                   # E.164 format: +15551234567
    address: Optional[str] = None

class CallContext(BaseModel):
    item_name: str
    item_description: str
    condition: str
    market_context: str
    estimated_price_range: dict         # { low, fair, high, currency }
    negotiation_strategy: NegotiationStrategy

class BatchCallRequest(BaseModel):
    call_name: str
    stores: list[StoreCallTarget]
    context: CallContext

class SingleCallRequest(BaseModel):
    store: StoreCallTarget
    context: CallContext

class CallOutcome(BaseModel):
    store_id: str
    store_name: str
    phone_number: str
    conversation_id: Optional[str] = None
    agent_id: Optional[str] = None
    call_status: str                    # "pending"|"in_progress"|"done"|"failed"
    call_successful: Optional[str] = None   # from analysis: "success"|"failure"|"unknown"
    willing_to_buy: Optional[bool] = None
    offered_price: Optional[float] = None
    transcript: list[dict] = []         # each item: role, message, time_in_call_secs, tool_calls, tool_results
    summary: Optional[str] = None
    call_summary_title: Optional[str] = None
    evaluation_criteria_results: dict = {}
    start_time_unix_secs: Optional[int] = None
    call_duration_secs: Optional[float] = None

class BatchCallStatus(BaseModel):
    batch_id: str
    status: str                         # "pending"|"in_progress"|"completed"|"failed"
    call_name: str
    total_scheduled: int
    total_dispatched: int
    total_finished: int
    outcomes: list[CallOutcome]

class SingleCallResponse(BaseModel):
    conversation_id: str
    call_sid: Optional[str] = None
    store_name: str

class ConversationInsight(BaseModel):
    owner_name: Optional[str] = None    # name of the person who called
    willing_to_sell: bool               # true = yes, false = no
    offered_price: Optional[float] = None  # null if not willing to sell


# ---- Negotiation models ----

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


# ---- Phone number models ----

class ImportPhoneNumberRequest(BaseModel):
    phone_number: str          # E.164 format: +15551234567
    label: str
    sid: Optional[str] = None  # Twilio Account SID (falls back to settings)
    token: Optional[str] = None  # Twilio Auth Token (falls back to settings)

class ImportPhoneNumberResponse(BaseModel):
    phone_number_id: str
    phone_number: str
    label: str


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


# ---- Calling helpers ----

def _build_dynamic_variables(store: StoreCallTarget, ctx: CallContext) -> dict:
    ns = ctx.negotiation_strategy
    return {
        "store_name": store.name,
        "item_name": ctx.item_name,
        "item_description": ctx.item_description,
        "condition": ctx.condition,
        "market_context": ctx.market_context,
        "price_low":   str(ctx.estimated_price_range.get("low", 0)),
        "price_fair":  str(ctx.estimated_price_range.get("fair", 0)),
        "price_high":  str(ctx.estimated_price_range.get("high", 0)),
        "opening_price":    str(ns.opening_price),
        "target_price":     str(ns.target_price),
        "walk_away_price":  str(ns.walk_away_price),
        "opening_script":   ns.opening_script,
        "counter_script":   ns.counter_script,
        "accept_script":    ns.accept_script,
        "walk_away_script": ns.walk_away_script,
    }


async def _fetch_conversation(conversation_id: str) -> dict:
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"https://api.elevenlabs.io/v1/convai/conversations/{conversation_id}",
            headers={"xi-api-key": settings.elevenlabs_api_key},
        )
        r.raise_for_status()
        return r.json()


async def _parse_transcript(transcript: list[dict]) -> tuple[Optional[bool], Optional[float]]:
    """Use Claude Haiku to extract yes/no + price when data_collection is not configured."""
    import anthropic
    text = "\n".join(
        f"{t.get('role','?')}: {t.get('message','')}" for t in transcript
    )
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=100,
        messages=[{"role": "user", "content": (
            "Transcript of a call where an agent is trying to sell an item to a store. "
            "Did the store agree to buy it? What price did they offer?\n\n"
            f"{text}\n\n"
            'Respond with JSON only: {"willing_to_buy": true/false/null, "offered_price": number/null}'
        )}],
    )
    try:
        r = json.loads(resp.content[0].text)
        price = r.get("offered_price")
        return r.get("willing_to_buy"), float(price) if price else None
    except Exception:
        return None, None


async def _extract_insights(transcript: list[dict]) -> ConversationInsight:
    """Use Claude Haiku to extract owner name, willingness to sell, and final price from a transcript.

    Transcript roles:
      - 'agent': the AI bot that placed the call (the buyer side)
      - 'user':  the store owner / seller on the other end of the call
    """
    import anthropic
    text = "\n".join(
        f"{t.get('role', '?')}: {t.get('message', '')}" for t in transcript
    )
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=150,
        messages=[{"role": "user", "content": (
            "Below is a transcript of a call. The 'agent' is an AI that called a store to buy an item. "
            "The 'user' is the store owner/seller. Extract exactly 3 fields:\n"
            "1. owner_name: the name of the store owner/seller ('user' side). "
            "Look for when the agent asks for a name and the user replies. null if not mentioned.\n"
            "2. willing_to_sell: true if the owner agreed to sell, false if they refused.\n"
            "3. offered_price: the FINAL price the owner accepted or last offered "
            "(NOT the opening ask — use the price the deal closed at or the last counter-offer). "
            "null if the owner is not willing to sell.\n\n"
            f"{text}\n\n"
            'Respond with JSON only: {"owner_name": string/null, "willing_to_sell": true/false, "offered_price": number/null}'
        )}],
    )
    try:
        r = json.loads(resp.content[0].text)
        price = r.get("offered_price")
        willing = bool(r.get("willing_to_sell", False))
        return ConversationInsight(
            owner_name=r.get("owner_name"),
            willing_to_sell=willing,
            offered_price=float(price) if (price is not None and willing) else None,
        )
    except Exception:
        return ConversationInsight(willing_to_sell=False)


async def _extract_outcome(
    conv: dict,
    store: StoreCallTarget,
) -> CallOutcome:
    analysis = conv.get("analysis", {})
    metadata = conv.get("metadata", {})
    # Each transcript item includes: role, message, time_in_call_secs,
    # tool_calls, tool_results, feedback, llm_usage, rag_retrieval_info
    transcript = conv.get("transcript", [])

    willing_to_buy: Optional[bool] = None
    offered_price: Optional[float] = None

    # Try data_collection_results first
    dc = analysis.get("data_collection_results", {})
    if "willing_to_buy" in dc:
        willing_to_buy = dc["willing_to_buy"].get("value")
    if "offered_price" in dc:
        raw = dc["offered_price"].get("value")
        try:
            offered_price = float(raw) if raw else None
        except (TypeError, ValueError):
            pass

    # Fallback: Claude Haiku parses the transcript
    if willing_to_buy is None and transcript:
        willing_to_buy, offered_price = await _parse_transcript(transcript)

    return CallOutcome(
        store_id=store.id,
        store_name=store.name,
        phone_number=store.phone_number,
        conversation_id=conv.get("conversation_id"),
        agent_id=conv.get("agent_id"),
        call_status=conv.get("status", "unknown"),
        call_successful=analysis.get("call_successful"),
        willing_to_buy=willing_to_buy,
        offered_price=offered_price,
        transcript=transcript,
        summary=analysis.get("transcript_summary"),
        call_summary_title=analysis.get("call_summary_title"),
        evaluation_criteria_results=analysis.get("evaluation_criteria_results") or {},
        start_time_unix_secs=metadata.get("start_time_unix_secs"),
        call_duration_secs=metadata.get("call_duration_secs"),
    )


# ==================== NEGOTIATION HELPERS ====================

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


@app.get("/api/agent/conversations/{conversation_id}/insights", response_model=ConversationInsight)
async def get_conversation_insights(conversation_id: str, user: dict = Depends(get_user)):
    """
    Fetch a conversation transcript from ElevenLabs and use Claude to extract:
    - owner_name: who was calling
    - willing_to_sell: boolean
    - offered_price: price if willing, else null
    """
    conv = await _fetch_conversation(conversation_id)
    transcript = conv.get("transcript", [])
    if not transcript:
        raise HTTPException(status_code=404, detail="No transcript found for this conversation")
    return await _extract_insights(transcript)


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


# ==================== PHONE NUMBER ROUTES ====================

@app.post("/api/calls/phone-numbers", response_model=ImportPhoneNumberResponse)
async def import_phone_number(req: ImportPhoneNumberRequest, user: dict = Depends(get_user)):
    """Import a Twilio phone number into ElevenLabs for outbound calling."""
    sid = req.sid or settings.twilio_account_sid
    token = req.token or settings.twilio_auth_token

    if not sid or not token:
        raise HTTPException(status_code=400, detail="Twilio SID and token are required")

    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://api.elevenlabs.io/v1/convai/phone-numbers",
            headers={"xi-api-key": settings.elevenlabs_api_key, "Content-Type": "application/json"},
            json={
                "provider": "twilio",
                "phone_number": req.phone_number,
                "label": req.label,
                "sid": sid,
                "token": token,
            },
        )
        r.raise_for_status()
        data = r.json()

    return ImportPhoneNumberResponse(
        phone_number_id=data["phone_number_id"],
        phone_number=req.phone_number,
        label=req.label,
    )


# ==================== CALLING ROUTES ====================

@app.post("/api/calls/batch", response_model=BatchCallStatus)
async def create_batch_call(req: BatchCallRequest, user: dict = Depends(get_user)):
    """Initiate a batch outbound call to multiple stores via ElevenLabs."""
    recipients = []
    for store in req.stores:
        recipients.append({
            "id": store.id,
            "phone_number": store.phone_number,
            "conversation_initiation_client_data": {
                "dynamic_variables": _build_dynamic_variables(store, req.context)
            }
        })

    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://api.elevenlabs.io/v1/convai/batch-calling/submit",
            headers={"xi-api-key": settings.elevenlabs_api_key, "Content-Type": "application/json"},
            json={
                "call_name": req.call_name,
                "agent_id": settings.elevenlabs_agent_id,
                "agent_phone_number_id": settings.elevenlabs_phone_number_id,
                "recipients": recipients,
            },
        )
        r.raise_for_status()
        data = r.json()

    return BatchCallStatus(
        batch_id=data["id"],
        status=data["status"],
        call_name=req.call_name,
        total_scheduled=data.get("total_calls_scheduled", len(req.stores)),
        total_dispatched=data.get("total_calls_dispatched", 0),
        total_finished=data.get("total_calls_finished", 0),
        outcomes=[],
    )


@app.get("/api/calls/batch/{batch_id}", response_model=BatchCallStatus)
async def get_batch_call(batch_id: str, user: dict = Depends(get_user)):
    """Poll batch call status and retrieve structured outcomes for completed calls."""
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"https://api.elevenlabs.io/v1/convai/batch-calling/{batch_id}",
            headers={"xi-api-key": settings.elevenlabs_api_key},
        )
        r.raise_for_status()
        data = r.json()

    outcomes: list[CallOutcome] = []
    for recipient in data.get("recipients", []):
        store = StoreCallTarget(
            id=recipient.get("id", ""),
            name=recipient.get("client_data", {}).get("dynamic_variables", {}).get("store_name", ""),
            phone_number=recipient.get("phone_number", ""),
        )
        conv_id = recipient.get("conversation_id")
        if conv_id:
            conv = await _fetch_conversation(conv_id)
            outcome = await _extract_outcome(conv, store)
        else:
            outcome = CallOutcome(
                store_id=store.id,
                store_name=store.name,
                phone_number=store.phone_number,
                call_status=recipient.get("status", "pending"),
            )
        outcomes.append(outcome)

    return BatchCallStatus(
        batch_id=data["id"],
        status=data["status"],
        call_name=data.get("name", ""),
        total_scheduled=data.get("total_calls_scheduled", 0),
        total_dispatched=data.get("total_calls_dispatched", 0),
        total_finished=data.get("total_calls_finished", 0),
        outcomes=outcomes,
    )


@app.post("/api/calls/single", response_model=SingleCallResponse)
async def create_single_call(req: SingleCallRequest, user: dict = Depends(get_user)):
    """Initiate a single outbound call to a store via ElevenLabs Twilio."""
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://api.elevenlabs.io/v1/convai/twilio/outbound-call",
            headers={"xi-api-key": settings.elevenlabs_api_key, "Content-Type": "application/json"},
            json={
                "agent_id": settings.elevenlabs_agent_id,
                "agent_phone_number_id": settings.elevenlabs_phone_number_id,
                "to_number": req.store.phone_number,
                "conversation_initiation_client_data": {
                    "dynamic_variables": _build_dynamic_variables(req.store, req.context)
                },
            },
        )
        r.raise_for_status()
        data = r.json()

    return SingleCallResponse(
        conversation_id=data.get("conversation_id", ""),
        call_sid=data.get("callSid"),
        store_name=req.store.name,
    )


@app.get("/api/calls/single/{conversation_id}", response_model=CallOutcome)
async def get_single_call_result(conversation_id: str, user: dict = Depends(get_user)):
    """Retrieve structured result for a completed single call."""
    conv = await _fetch_conversation(conversation_id)
    dv = conv.get("metadata", {}).get("dynamic_variables", {})
    store = StoreCallTarget(
        id=conversation_id,
        name=dv.get("store_name", "Unknown"),
        phone_number=conv.get("metadata", {}).get("phone_call", {}).get("to_number", ""),
    )
    return await _extract_outcome(conv, store)


@app.post("/api/calls/webhook")
async def calls_webhook(request: Request):
    """
    Post-call transcription webhook from ElevenLabs (no auth required).
    Configure URL in ElevenLabs dashboard > Agent > Advanced > Webhooks.
    """
    data = await request.json()
    event_type = data.get("type")
    if event_type == "post_call_transcription":
        conv_data = data.get("data", {})
        print(f"[Webhook] Call complete: {conv_data.get('conversation_id')} | "
              f"status: {conv_data.get('analysis', {}).get('call_successful')}")
        # Extend here to persist to Supabase if needed
    return {"status": "received"}


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

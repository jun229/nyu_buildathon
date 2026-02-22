"""
Vision-to-Appraisal Ensemble Agent
====================================
Node 1 (Vision):    Claude Opus 4.6   — identifies item + assesses condition from photo
Node 2 (Swarm):     5 × NVIDIA Nemotron workers in parallel
                      • Online marketplace price analyst
                      • Local marketplace price analyst
                      • Condition-to-value impact analyst
                      • Market demand & trends analyst
                      • Pawn / resale shop valuation specialist
Node 2b (Shops):    SearchAPI.io Google Maps — finds REAL nearby shops with phone numbers
                    (runs in parallel with the Nemotron swarm)
Node 3 (Synthesis): Claude Opus 4.6   — produces a voice-agent JSON payload

Graph:              LangGraph StateGraph with parallel fan-out

Usage:
  python agent.py path/to/item.jpg --ll "@40.7009973,-73.994778"
"""

import argparse
import asyncio
import base64
import json
import os
import re
import sys
from typing import Any

import anthropic
import requests
from dotenv import load_dotenv
from langgraph.graph import END, StateGraph
from openai import AsyncOpenAI
from typing_extensions import TypedDict

# ---------------------------------------------------------------------------
# Load .env from the same directory as this script
# ---------------------------------------------------------------------------
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_SCRIPT_DIR, ".env"))


# ---------------------------------------------------------------------------
# Environment validation — fail fast with clear messages
# ---------------------------------------------------------------------------
def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        print(f"[ERROR] Missing required environment variable: {name}")
        print(f"        Add it to agents/.env or export it in your shell.")
        sys.exit(1)
    return value


ANTHROPIC_API_KEY = _require_env("ANTHROPIC_API_KEY")
NVIDIA_API_KEY = _require_env("NVIDIA_API_KEY")
SEARCHAPI_KEY = _require_env("SEARCHAPI_KEY")


# ---------------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------------
claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
CLAUDE_MODEL = "claude-opus-4-6"

nvidia = AsyncOpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=NVIDIA_API_KEY,
)
NVIDIA_MODEL = "nvidia/nemotron-3-nano-30b-a3b"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _strip_json(text: str) -> str:
    """Extract JSON from text that may be wrapped in markdown code fences."""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        return text[start : end + 1]
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end > start:
        return text[start : end + 1]
    return text


def _parse_json(raw: str) -> dict:
    """Parse text expected to contain JSON. Returns dict with parse_error on failure."""
    cleaned = _strip_json(raw)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {"raw": cleaned, "parse_error": True}


def _image_to_base64(path: str) -> tuple[str, str]:
    """Read a local image and return (base64_data, media_type).
    Detects actual format from file header (magic bytes), not just the extension.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Image not found: {path}")
    with open(path, "rb") as f:
        data = f.read()
    # Detect actual format from magic bytes (file extensions can lie)
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        mime = "image/png"
    elif data[:2] == b'\xff\xd8':
        mime = "image/jpeg"
    elif data[:4] == b'GIF8':
        mime = "image/gif"
    elif data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        mime = "image/webp"
    else:
        # Fall back to extension
        ext = os.path.splitext(path)[1].lower()
        mime = {
            ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".png": "image/png", ".gif": "image/gif", ".webp": "image/webp",
        }.get(ext)
        if not mime:
            raise ValueError(f"Cannot detect image format for: {path}")
    return base64.standard_b64encode(data).decode(), mime


def _call_claude(system: str, user_content, max_tokens: int = 2048) -> str:
    """Call Claude Messages API with error handling."""
    try:
        resp = claude.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user_content}],
        )
        return resp.content[0].text.strip()
    except anthropic.AuthenticationError:
        print("[ERROR] Invalid ANTHROPIC_API_KEY. Check agents/.env")
        sys.exit(1)
    except anthropic.APIError as e:
        print(f"[ERROR] Claude API: {e}")
        raise


# ---------------------------------------------------------------------------
# Graph state
# ---------------------------------------------------------------------------
class AgentState(TypedDict):
    image_path: str
    user_location: str
    identified_item: str
    condition_details: str
    swarm_results: list[dict[str, Any]]
    nearby_shops: list[dict[str, Any]]
    final_payload: dict[str, Any]


# ═══════════════════════════════════════════════════════════════════════════
# NODE 1 — VISION (Claude Opus 4.6)
# ═══════════════════════════════════════════════════════════════════════════

_VISION_SYSTEM = (
    "You are an expert appraiser with decades of experience valuing consumer goods, "
    "electronics, jewelry, vehicles, collectibles, and sporting equipment. "
    "You identify items precisely and assess condition honestly for resale. "
    "Always respond with ONLY valid JSON — no markdown fences, no commentary."
)

_VISION_PROMPT = """\
Examine the item in this image carefully.

Respond with ONLY this JSON (no other text):
{
  "item_name": "Full identification — brand, model, year/generation, color, size. Be as specific as possible.",
  "category": "One of: electronics, jewelry, furniture, clothing, sporting_goods, tools, collectibles, vehicles, musical_instruments, appliances, other",
  "condition_grade": "One of: like_new, excellent, good, fair, poor",
  "condition_details": "2-3 sentences on visible wear, scratches, dents, discoloration, missing parts, completeness. If it looks new, say so.",
  "notable_features": "Accessories visible, limited edition markers, original packaging, modifications, damage",
  "estimated_age": "Best estimate based on visual cues (e.g. '2-3 years', 'vintage circa 1990s')"
}

Rules:
- If you cannot identify the exact brand/model, describe it as specifically as you can.
- Err on the side of noting imperfections — a buyer will find them.
- Do NOT hedge with "it might be" — give your best identification confidently."""


def vision_node(state: AgentState) -> dict:
    """Send the photo to Claude Opus for item identification and condition grading."""
    print("\n[1/4 VISION] Claude Opus analyzing image...")
    img_data, mime = _image_to_base64(state["image_path"])

    raw = _call_claude(
        system=_VISION_SYSTEM,
        user_content=[
            {
                "type": "image",
                "source": {"type": "base64", "media_type": mime, "data": img_data},
            },
            {"type": "text", "text": _VISION_PROMPT},
        ],
        max_tokens=1024,
    )

    data = _parse_json(raw)

    if data.get("parse_error"):
        print("[VISION] Warning: couldn't parse JSON, using raw response")
        return {
            "identified_item": raw[:300],
            "condition_details": json.dumps({"raw_description": raw}),
        }

    item = data.get("item_name", "Unknown item")
    grade = data.get("condition_grade", "unknown")
    print(f"[VISION] Identified: {item}")
    print(f"[VISION] Condition: {grade}")

    return {
        "identified_item": item,
        "condition_details": json.dumps(data, indent=2),
    }


# ═══════════════════════════════════════════════════════════════════════════
# NODE 2a — NEMOTRON SWARM (5 workers in parallel)
# ═══════════════════════════════════════════════════════════════════════════

SWARM_WORKERS = [
    {
        "name": "online_marketplace_analyst",
        "label": "Online Marketplace Prices",
        "prompt": """\
You are a price research analyst specializing in eBay, Amazon resale, Mercari, and similar online marketplaces.

Item: {item}
Condition: {condition}

Based on your knowledge of current market prices, estimate what this item would realistically sell for on major online marketplaces.

Return ONLY valid JSON:
{{
  "source": "online_marketplaces",
  "platforms": [
    {{"name": "eBay", "estimated_sold_price": <number USD>, "listing_price": <number USD>, "sell_through_rate": "high/medium/low"}},
    {{"name": "Mercari", "estimated_sold_price": <number USD>, "listing_price": <number USD>, "sell_through_rate": "high/medium/low"}},
    {{"name": "Amazon Resale", "estimated_sold_price": <number USD>, "listing_price": <number USD>, "sell_through_rate": "high/medium/low"}}
  ],
  "average_sold_price": <number USD>,
  "price_range_low": <number USD>,
  "price_range_high": <number USD>,
  "notes": "One sentence on online marketplace dynamics for this item"
}}""",
    },
    {
        "name": "local_marketplace_analyst",
        "label": "Local Marketplace Prices",
        "prompt": """\
You are a local marketplace analyst specializing in Facebook Marketplace, Craigslist, and OfferUp — platforms where buyers pick up items locally.

Item: {item}
Condition: {condition}

Local prices are typically 10-20% lower than online due to no shipping, instant cash, and negotiation. Estimate realistic local selling prices.

Return ONLY valid JSON:
{{
  "source": "local_marketplaces",
  "platforms": [
    {{"name": "Facebook Marketplace", "estimated_price": <number USD>, "typical_days_to_sell": <number>}},
    {{"name": "Craigslist", "estimated_price": <number USD>, "typical_days_to_sell": <number>}},
    {{"name": "OfferUp", "estimated_price": <number USD>, "typical_days_to_sell": <number>}}
  ],
  "average_local_price": <number USD>,
  "negotiation_discount_pct": <number — typical % buyers negotiate down>,
  "notes": "One sentence on local market dynamics"
}}""",
    },
    {
        "name": "condition_impact_analyst",
        "label": "Condition Impact Analysis",
        "prompt": """\
You are an expert at assessing how condition affects resale value. You understand grading scales and what buyers pay attention to.

Item: {item}
Condition details: {condition}

Calculate the price adjustment based on condition. A mint/sealed item is the baseline (100%). Deduct based on wear, damage, missing parts, age.

Return ONLY valid JSON:
{{
  "source": "condition_analysis",
  "condition_grade": "like_new/excellent/good/fair/poor",
  "value_retention_pct": <number — percentage of mint value retained, e.g. 85 for good condition>,
  "deductions": [
    {{"factor": "description of wear/damage", "impact_pct": <negative number, e.g. -5>}}
  ],
  "mint_value_estimate": <number USD — what this item would be worth if perfect>,
  "condition_adjusted_value": <number USD — mint value × retention percentage>,
  "notes": "One sentence on how this condition compares to typical listings"
}}""",
    },
    {
        "name": "market_demand_analyst",
        "label": "Market Demand & Trends",
        "prompt": """\
You are a market trends analyst who tracks consumer demand, seasonal patterns, and price trajectories for resale goods.

Item: {item}
Condition: {condition}

Assess the current market demand for this item. Consider: Is it trending up or down? Is there seasonal demand? Is it being discontinued? Is supply flooding the market?

Return ONLY valid JSON:
{{
  "source": "market_demand",
  "demand_level": "very_high/high/medium/low/very_low",
  "price_trend": "appreciating/stable/depreciating",
  "depreciation_rate_annual_pct": <number — estimated annual depreciation, e.g. 15>,
  "seasonal_factors": "One sentence on seasonal demand patterns",
  "supply_level": "scarce/normal/oversupplied",
  "best_time_to_sell": "now/wait/seasonal — one word then explanation",
  "liquidity": "high/medium/low — how quickly it would sell",
  "notes": "One sentence on overall market outlook"
}}""",
    },
    {
        "name": "pawn_resale_specialist",
        "label": "Pawn & Resale Shop Valuation",
        "prompt": """\
You are a pawn shop and resale industry expert. You know how pawn shops, consignment stores, and specialty resale shops price and make offers.

Item: {item}
Condition: {condition}

Pawn shops typically offer 30-60% of resale value. Specialty shops (e.g. bike shops for bikes, music stores for instruments) offer 40-70%. Consignment takes 30-50% commission.

Return ONLY valid JSON:
{{
  "source": "pawn_resale_valuation",
  "pawn_shop": {{
    "offer_low": <number USD — lowball pawn offer>,
    "offer_high": <number USD — good pawn offer>,
    "typical_offer": <number USD>,
    "notes": "What affects pawn pricing for this item"
  }},
  "specialty_shop": {{
    "offer_low": <number USD>,
    "offer_high": <number USD>,
    "typical_offer": <number USD>,
    "notes": "Why specialty shops may pay more/less"
  }},
  "consignment": {{
    "listing_price": <number USD — what they'd list it for>,
    "your_take": <number USD — after commission>,
    "commission_pct": <number>,
    "notes": "Typical consignment terms"
  }},
  "recommendation": "pawn/specialty/consignment — which channel is best for this item and why"
}}""",
    },
]


async def _run_nemotron_worker(
    worker: dict, identified_item: str, condition: str
) -> dict[str, Any]:
    """Run a single Nemotron worker and return its analysis."""
    name = worker["name"]
    label = worker["label"]
    print(f"  [SWARM] {label}...")

    prompt = worker["prompt"].format(item=identified_item, condition=condition)

    try:
        completion = await nvidia.chat.completions.create(
            model=NVIDIA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            top_p=0.9,
            max_tokens=4096,
        )
        content = completion.choices[0].message.content or ""
    except Exception as e:
        print(f"  [SWARM] {label} FAILED: {e}")
        return {"worker": name, "error": str(e)}

    content = _strip_json(content)

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        parsed = {"raw": content, "parse_error": True}

    return {"worker": name, "label": label, "result": parsed}


async def _run_all_workers(
    identified_item: str, condition: str
) -> list[dict[str, Any]]:
    """Fan out all Nemotron workers concurrently."""
    tasks = [
        _run_nemotron_worker(w, identified_item, condition)
        for w in SWARM_WORKERS
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Convert exceptions to error dicts
    clean = []
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            name = SWARM_WORKERS[i]["name"]
            print(f"  [SWARM] {name} crashed: {r}")
            clean.append({"worker": name, "error": str(r)})
        else:
            clean.append(r)
    return clean


def swarm_node(state: AgentState) -> dict:
    """Launch all Nemotron workers in parallel for market analysis."""
    print(f"\n[2/4 SWARM] Launching {len(SWARM_WORKERS)} Nemotron workers...")

    # Handle nested event loops (e.g. if LangGraph uses async internally)
    try:
        loop = asyncio.get_running_loop()
        # Already in an event loop — use nest_asyncio
        import nest_asyncio
        nest_asyncio.apply()
        results = loop.run_until_complete(
            _run_all_workers(state["identified_item"], state["condition_details"])
        )
    except RuntimeError:
        # No running event loop — safe to use asyncio.run
        results = asyncio.run(
            _run_all_workers(state["identified_item"], state["condition_details"])
        )

    successful = sum(1 for r in results if "error" not in r)
    print(f"[SWARM] {successful}/{len(results)} workers completed successfully.")

    return {"swarm_results": results}


# ═══════════════════════════════════════════════════════════════════════════
# NODE 2b — SHOP FINDER (SearchAPI.io Google Maps)
# Docs: https://www.searchapi.io/docs/google-maps
# ═══════════════════════════════════════════════════════════════════════════

_SEARCHAPI_URL = "https://www.searchapi.io/api/v1/search"
_SEARCH_RADIUS_M = 16093  # 10 miles in meters

_SPECIALTY_MAP = [
    (["bike", "bicycle", "cycling", "trek", "specialized"], "bike shop"),
    (["guitar", "bass", "drum", "piano", "keyboard", "instrument", "music", "fender", "gibson"], "music store"),
    (["phone", "iphone", "samsung", "android", "tablet", "ipad"], "electronics buyback store"),
    (["laptop", "macbook", "computer", "pc", "dell", "hp", "lenovo"], "computer repair shop"),
    (["camera", "lens", "canon", "nikon", "sony alpha", "fujifilm"], "camera store"),
    (["watch", "rolex", "omega", "seiko", "cartier", "tag heuer"], "watch dealer"),
    (["ring", "necklace", "bracelet", "gold", "silver", "diamond", "jewelry"], "jewelry buyer"),
    (["sneaker", "jordan", "nike", "yeezy", "shoe", "air max"], "sneaker resale store"),
    (["vinyl", "record", "turntable"], "record store"),
    (["game", "playstation", "xbox", "nintendo", "console", "ps5"], "video game store"),
    (["tool", "drill", "saw", "wrench", "dewalt", "milwaukee", "makita"], "used tool store"),
    (["furniture", "couch", "sofa", "table", "chair", "desk"], "used furniture store"),
    (["vintage", "antique", "retro"], "antique shop"),
    (["clothing", "jacket", "coat", "dress", "designer"], "consignment shop"),
    (["bag", "purse", "louis vuitton", "gucci", "handbag", "chanel", "prada"], "luxury consignment"),
    (["golf", "club", "titleist", "callaway", "taylormade"], "golf shop"),
    (["ski", "snowboard", "burton", "rossignol"], "ski shop"),
]


def _specialty_query(item: str) -> str:
    low = item.lower()
    for keywords, query in _SPECIALTY_MAP:
        if any(k in low for k in keywords):
            return query
    return ""


def _search_google_maps(query: str, ll: str) -> list[dict]:
    """Search for shops via SearchAPI.io Google Maps engine.

    Args:
        query: Search term (e.g. "pawn shop").
        ll:    GPS coordinates string in SearchAPI ll format,
               e.g. "@40.7009973,-73.994778,12z"
    """
    params = {
        "engine": "google_maps",
        "q": query,
        "ll": f"{ll},{_SEARCH_RADIUS_M}m",
        "api_key": SEARCHAPI_KEY,
    }
    try:
        r = requests.get(_SEARCHAPI_URL, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
    except requests.RequestException as e:
        print(f"  [SHOPS] SearchAPI error for '{query}': {e}")
        return []

    shops = []
    for p in data.get("local_results", []):
        shops.append({
            "name": p.get("title", "Unknown"),
            "address": p.get("address", ""),
            "phone": p.get("phone", ""),
            "rating": p.get("rating"),
            "review_count": p.get("reviews"),
            "website": p.get("website", ""),
            "type": p.get("type", ""),
        })
    return shops


def shop_finder_node(state: AgentState) -> dict:
    """Find nearby shops via SearchAPI.io Google Maps."""
    item = state["identified_item"]
    ll = state["user_location"]
    print(f"\n[3/4 SHOPS] Searching Google Maps via SearchAPI at {ll}...")

    all_shops: list[dict] = []

    # Search 1: Pawn shops
    print("  [SHOPS] Searching: pawn shops")
    pawn = _search_google_maps("pawn shop", ll)
    for s in pawn:
        s["shop_type"] = "pawn"
    all_shops.extend(pawn)

    # Search 2: Specialty shops matching the item
    spec_q = _specialty_query(item)
    if spec_q:
        print(f"  [SHOPS] Searching: {spec_q}")
        spec = _search_google_maps(spec_q, ll)
        for s in spec:
            s["shop_type"] = "specialty"
        all_shops.extend(spec)

    # Search 3: "sell/buy used" shops
    buy_q = f"sell used {spec_q or 'items'}"
    print(f"  [SHOPS] Searching: {buy_q}")
    buyers = _search_google_maps(buy_q, ll)
    for s in buyers:
        s["shop_type"] = "buyer"
    all_shops.extend(buyers)

    # Deduplicate by name
    seen = set()
    unique = []
    for s in all_shops:
        if s["name"] not in seen:
            seen.add(s["name"])
            unique.append(s)

    for s in unique:
        s["data_source"] = "searchapi_google_maps"

    with_phone = [s for s in unique if s.get("phone")]
    print(f"[SHOPS] {len(unique)} shops found, {len(with_phone)} with phone numbers")

    return {"nearby_shops": with_phone if with_phone else unique}


# ═══════════════════════════════════════════════════════════════════════════
# NODE 3 — SYNTHESIS (Claude Opus 4.6) → Voice Agent Payload
# ═══════════════════════════════════════════════════════════════════════════

_SYNTH_SYSTEM = (
    "You produce structured JSON briefings for an AI voice agent that will call shops "
    "to negotiate selling an item on behalf of the user. The voice agent reads the scripts "
    "verbatim, so make them natural and conversational. Include specific dollar amounts. "
    "Respond with ONLY valid JSON — no markdown fences, no commentary."
)

_SYNTH_PROMPT = """\
Synthesize all research data below into a single voice-agent briefing.

ITEM IDENTIFICATION:
{item}

CONDITION:
{condition}

NEMOTRON SWARM ANALYSIS (5 independent market analysts):
{swarm}

NEARBY SHOPS (with contact info):
{shops}

Return ONLY this JSON:
{{
  "item_name": "Short name for phone conversations (e.g. '2023 Trek Domane SL5 road bike')",
  "item_description": "One natural sentence the agent says to describe the item's condition on a call",
  "estimated_market_value": {{
    "low": <number — quick-sale price from swarm data>,
    "fair": <number — consensus fair value across all swarm analysts>,
    "high": <number — patient-seller price from swarm data>
  }},
  "market_context": "2-3 sentences the voice agent can use on calls to justify its price — cite specific data points from the swarm analysis",
  "target_shops": [
    {{
      "name": "Exact shop name",
      "address": "Full address",
      "phone": "Phone number exactly as provided in the shop data",
      "shop_type": "pawn | specialty | buyer",
      "rating": <number or null>,
      "priority": <1 = call first, 2 = second, etc.>,
      "reason": "One sentence: why this shop is a good fit for this item"
    }}
  ],
  "negotiation_strategy": {{
    "opening_price": <number — aim high, use the swarm high estimate>,
    "target_price": <number — realistic goal, use the swarm fair estimate>,
    "walk_away_price": <number — absolute minimum, use max(pawn_typical_offer, fair * 0.55)>,
    "opening_script": "Fill in real values: Hi, I'm calling to see if you'd be interested in purchasing a [real item name]. It's in [real condition] condition. I've seen similar ones selling for around $[opening_price] online. Would you be interested in taking a look?",
    "counter_script": "Fill in real values: I appreciate the offer. Given the current market — [cite one fact from market_context] — I was hoping for closer to $[target_price]. Would you be able to come up a bit?",
    "accept_script": "That works for me. When would be a good time to bring it in?",
    "walk_away_script": "I appreciate your time. I'll think it over and may circle back. Thanks!"
  }}
}}

Rules:
- ONLY include shops that have phone numbers in target_shops.
- Sort by priority: specialty first, buyers second, pawn last. Higher-rated shops first within each type.
- Fill in ALL dollar amounts and item details in the scripts — NO placeholders like [item_name].
- Cross-reference all 5 swarm analysts to find a consensus price range. If analysts disagree significantly, use the median.
- The walk_away_price should never be lower than the pawn_shop typical_offer from the swarm data."""


def synthesis_node(state: AgentState) -> dict:
    """Combine Nemotron swarm analyses + real shop data into the voice-agent payload."""
    print("\n[4/4 SYNTHESIS] Claude Opus building voice-agent payload...")

    raw = _call_claude(
        system=_SYNTH_SYSTEM,
        user_content=_SYNTH_PROMPT.format(
            item=state["identified_item"],
            condition=state["condition_details"],
            swarm=json.dumps(state["swarm_results"], indent=2),
            shops=json.dumps(state["nearby_shops"], indent=2),
        ),
        max_tokens=4096,
    )

    payload = _parse_json(raw)

    if payload.get("parse_error"):
        print("[SYNTHESIS] Warning: couldn't parse JSON response")
    else:
        n_shops = len(payload.get("target_shops", []))
        strat = payload.get("negotiation_strategy", {})
        opening = strat.get("opening_price", "?")
        walkaway = strat.get("walk_away_price", "?")
        print(f"[SYNTHESIS] {n_shops} shops | open at ${opening} | walk away at ${walkaway}")

    return {"final_payload": payload}


# ═══════════════════════════════════════════════════════════════════════════
# GRAPH
# ═══════════════════════════════════════════════════════════════════════════

def build_graph():
    g = StateGraph(AgentState)

    g.add_node("vision", vision_node)
    g.add_node("swarm", swarm_node)
    g.add_node("shops", shop_finder_node)
    g.add_node("synthesis", synthesis_node)

    g.set_entry_point("vision")
    # After vision, swarm and shops run in parallel (fan-out)
    g.add_edge("vision", "swarm")
    g.add_edge("vision", "shops")
    # Both must complete before synthesis (fan-in)
    g.add_edge("swarm", "synthesis")
    g.add_edge("shops", "synthesis")
    g.add_edge("synthesis", END)

    return g.compile()


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def run(image_path: str, location: str = "@40.7009973,-73.994778") -> dict:
    """Run the full appraisal pipeline. Returns the final state dict.

    Args:
        location: GPS coordinates as "@latitude,longitude". A fixed 10-mile search
                  radius is appended automatically.
    """
    if not os.path.isabs(image_path):
        image_path = os.path.join(_SCRIPT_DIR, image_path)

    if not os.path.isfile(image_path):
        print(f"[ERROR] Image not found: {image_path}")
        sys.exit(1)

    print("=" * 60)
    print("  APPRAISAL AGENT — Vision + Nemotron Swarm + SearchAPI")
    print("=" * 60)
    print(f"  Image:      {os.path.basename(image_path)}")
    print(f"  Location:   {location}")
    print(f"  Vision:     {CLAUDE_MODEL}")
    print(f"  Swarm:      {len(SWARM_WORKERS)}x {NVIDIA_MODEL}")
    print(f"  Shops:      SearchAPI.io Google Maps")
    print(f"  Synthesis:  {CLAUDE_MODEL}")
    print("=" * 60)

    app = build_graph()

    result = app.invoke({
        "image_path": image_path,
        "user_location": location,
        "identified_item": "",
        "condition_details": "",
        "swarm_results": [],
        "nearby_shops": [],
        "final_payload": {},
    })

    print("\n" + "=" * 60)
    print("  VOICE AGENT PAYLOAD")
    print("=" * 60)
    print(json.dumps(result["final_payload"], indent=2))
    print("=" * 60)

    out = os.path.join(_SCRIPT_DIR, "payload.json")
    with open(out, "w") as f:
        json.dump(result["final_payload"], f, indent=2)
    print(f"\nSaved to: {out}")

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Appraise an item from a photo and find shops to sell it"
    )
    parser.add_argument(
        "image", nargs="?", default="sample_item.jpg",
        help="Path to the item image (default: sample_item.jpg)",
    )
    parser.add_argument(
        "--ll", "-l", default="@40.7009973,-73.994778",
        help='GPS coordinates: "@latitude,longitude" (default: @40.7009973,-73.994778 — Manhattan)',
    )
    args = parser.parse_args()
    run(image_path=args.image, location=args.ll)


if __name__ == "__main__":
    main()

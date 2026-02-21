"""
Vision-to-Swarm Ensemble Agent
===============================
Node 1 (Vision):    Claude Opus 4.6  — identifies item from a local image
Node 2 (Swarm):     7 × NVIDIA Nemotron workers in parallel
                      • 3 price scrapers   (eBay, Craigslist, Facebook Marketplace)
                      • 2 social signals   (Reddit, Twitter)
                      • 2 local shops      (Google Places: pawn, specialty)
Node 3 (Synthesis): Claude Opus 4.6  — produces a strict ElevenLabs voice-agent JSON payload
Graph:              LangGraph StateGraph
"""

import asyncio
import base64
import json
import os
from typing import Any

import anthropic
from dotenv import load_dotenv
from langgraph.graph import END, StateGraph
from openai import AsyncOpenAI
from typing_extensions import TypedDict

load_dotenv()

# ---------------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------------

anthropic_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

nvidia_client = AsyncOpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.environ.get("NVIDIA_API_KEY"),
)

# ---------------------------------------------------------------------------
# Image Helper
# ---------------------------------------------------------------------------


def image_to_base64(image_path: str) -> tuple[str, str]:
    """Convert a local image file to a base64 string and infer its MIME type."""
    ext = os.path.splitext(image_path)[1].lower()
    media_type_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    media_type = media_type_map.get(ext, "image/jpeg")
    with open(image_path, "rb") as fh:
        data = base64.standard_b64encode(fh.read()).decode("utf-8")
    return data, media_type


# ---------------------------------------------------------------------------
# Graph State
# ---------------------------------------------------------------------------


class AgentState(TypedDict):
    image_path: str                      # path to the local image file
    identified_item: str                 # Vision node output — what Opus sees
    swarm_results: list[dict[str, Any]]  # aggregated outputs from all 7 workers
    final_payload: dict[str, Any]        # ElevenLabs-formatted JSON schema


# ---------------------------------------------------------------------------
# Swarm Task Definitions  (7 workers)
# ---------------------------------------------------------------------------

SWARM_TASKS: list[dict[str, str]] = [
    # --- 3 Price workers ---
    {
        "worker_type": "price",
        "source": "eBay",
        "url": "https://www.ebay.com/sch/i.html?_nkw={item}",
    },
    {
        "worker_type": "price",
        "source": "Craigslist",
        "url": "https://craigslist.org/search/sss?query={item}",
    },
    {
        "worker_type": "price",
        "source": "Facebook Marketplace",
        "url": "https://www.facebook.com/marketplace/search/?query={item}",
    },
    # --- 2 Social workers ---
    {
        "worker_type": "social",
        "source": "Reddit",
        "url": "https://www.reddit.com/search/?q={item}",
    },
    {
        "worker_type": "social",
        "source": "Twitter",
        "url": "https://twitter.com/search?q={item}",
    },
    # --- 2 Google Places workers ---
    {
        "worker_type": "places",
        "source": "Google Places - Pawn Shops",
        "url": "https://maps.googleapis.com/maps/api/place/textsearch/json?query=pawn+shops+near+me",
    },
    {
        "worker_type": "places",
        "source": "Google Places - Specialty Shops",
        "url": "https://maps.googleapis.com/maps/api/place/textsearch/json?query={item}+shop+near+me",
    },
]


# ---------------------------------------------------------------------------
# Node 1 — Vision (Claude Opus 4.6)
# ---------------------------------------------------------------------------


def vision_node(state: AgentState) -> AgentState:
    """
    Sends the local image to Claude Opus 4.6 with vision.
    Opus identifies the item in the center of the frame and stores it as identified_item.
    """
    print("\n[VISION] Claude Opus 4.6 is analysing the image...")

    image_data, media_type = image_to_base64(state["image_path"])

    response = anthropic_client.messages.create(
        model="claude-opus-4-6",
        max_tokens=512,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            "Look at the item in the center of this image. "
                            "Identify it as precisely as possible — include brand, model, year, "
                            "condition, and any visible features or specifications. "
                            "Respond with a single concise sentence, for example: "
                            "'2024 Specialized Stumpjumper Comp Alloy 29 mountain bike in "
                            "Gloss Moss Green, size Medium, appears lightly used.'"
                        ),
                    },
                ],
            }
        ],
    )

    identified_item = response.content[0].text.strip()
    print(f"[VISION] Identified: {identified_item}")

    return {**state, "identified_item": identified_item}


# ---------------------------------------------------------------------------
# Node 2 — Swarm (7 × NVIDIA Nemotron via AsyncOpenAI)
# ---------------------------------------------------------------------------


def _build_prompt(task: dict[str, str], identified_item: str) -> str:
    """Build a worker-type-specific prompt + mock data for Nemotron."""
    url = task["url"].replace("{item}", identified_item.replace(" ", "+"))

    if task["worker_type"] == "price":
        mock_data = (
            f"Mock listings from {task['source']} for '{identified_item}':\n"
            "Listing 1: $3,299.00 — good condition, ships nationwide\n"
            "Listing 2: $3,050.00 — used, local pickup only\n"
            "Listing 3: $3,499.99 — new in box, sealed\n"
            "Listing 4: $2,850.00 — scratched frame, otherwise functional\n"
            "Listing 5: $3,100.00 — like new, under 50 miles\n"
        )
        return (
            f"You are a price intelligence agent. Analyse these mock search results.\n\n"
            f"Item: {identified_item}\nSource: {task['source']}\nURL: {url}\n\n"
            f"Data:\n{mock_data}\n\n"
            "Return ONLY valid JSON with exactly these keys:\n"
            "  source (string), listings (array of objects with title/price/condition),\n"
            "  lowest_price (number), highest_price (number), average_price (number)"
        )

    elif task["worker_type"] == "social":
        mock_data = (
            f"Mock {task['source']} posts about '{identified_item}':\n"
            "Post 1 (upvotes: 342): 'Finally sold mine for $3,200 after 3 days — market is hot'\n"
            "Post 2 (upvotes: 128): 'Paid $3,400 new; used ones moving for $2,900–$3,100'\n"
            "Post 3 (upvotes: 89): 'LFS offering $2,600 trade-in — seems low, go private'\n"
            "Post 4 (upvotes: 67): 'Demand strong heading into spring riding season'\n"
        )
        return (
            f"You are a social sentiment agent. Analyse these mock {task['source']} posts.\n\n"
            f"Item: {identified_item}\nPlatform: {task['source']}\nURL: {url}\n\n"
            f"Data:\n{mock_data}\n\n"
            "Return ONLY valid JSON with exactly these keys:\n"
            "  platform (string), overall_sentiment (string: positive/neutral/negative),\n"
            "  liquidity (string: high/medium/low), average_days_to_sell (number),\n"
            "  community_price_range (string), key_insights (array of strings)"
        )

    else:  # places
        shop_type = "pawn" if "Pawn" in task["source"] else "specialty"
        mock_data = (
            f"Mock Google Places results for {shop_type} shops near user:\n"
            "Shop 1: Midtown Pawn & Jewelry — 123 W 42nd St, New York, NY 10036 — (212) 555-0101 — 4.2★\n"
            "Shop 2: Big Apple Pawn — 456 Broadway, New York, NY 10013 — (212) 555-0188 — 3.9★\n"
            "Shop 3: NYC Bike Exchange — 789 Amsterdam Ave, New York, NY 10025 — (212) 555-0134 — 4.6★\n"
            "Shop 4: Urban Velo — 321 Park Ave S, New York, NY 10010 — (212) 555-0177 — 4.4★\n"
        )
        return (
            f"You are a local shop finder agent. Analyse these mock Google Places results.\n\n"
            f"Item to sell: {identified_item}\nShop type: {shop_type}\nURL: {url}\n\n"
            f"Data:\n{mock_data}\n\n"
            "Return ONLY valid JSON with exactly these keys:\n"
            "  shop_type (string), shops (array of objects with name/address/phone/rating)"
        )


def _strip_fences(text: str) -> str:
    """Remove markdown code fences from a string."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    return text


async def _run_swarm_worker(task: dict[str, str], identified_item: str) -> dict[str, Any]:
    """Run a single Nemotron sub-agent for a given swarm task."""
    print(f"  [SWARM] {task['worker_type'].upper()} worker → {task['source']}")

    prompt = _build_prompt(task, identified_item)

    completion = await nvidia_client.chat.completions.create(
        model="nvidia/nemotron-3-nano-30b-a3b",
        messages=[{"role": "user", "content": prompt}],
        temperature=1,
        top_p=1,
        max_tokens=16384,
        extra_body={
            "reasoning_budget": 16384,
            "chat_template_kwargs": {"enable_thinking": True},
        },
        stream=True,
    )

    reasoning_output = ""
    content_output = ""

    async for chunk in completion:
        if not chunk.choices:
            continue
        reasoning = getattr(chunk.choices[0].delta, "reasoning_content", None)
        if reasoning:
            reasoning_output += reasoning
        if chunk.choices[0].delta.content is not None:
            content_output += chunk.choices[0].delta.content

    content_output = _strip_fences(content_output)

    try:
        parsed = json.loads(content_output)
    except json.JSONDecodeError:
        parsed = {"raw": content_output}

    return {
        "worker_type": task["worker_type"],
        "source": task["source"],
        "result": parsed,
        "reasoning_tokens": len(reasoning_output.split()),
    }


async def _run_all_workers(identified_item: str) -> list[dict[str, Any]]:
    """Fan out all 7 swarm workers concurrently."""
    return await asyncio.gather(
        *[_run_swarm_worker(t, identified_item) for t in SWARM_TASKS]
    )


def swarm_node(state: AgentState) -> AgentState:
    """Sync wrapper that launches all 7 async Nemotron workers via asyncio.run()."""
    print(f"\n[SWARM] Launching 7 concurrent Nemotron workers for: {state['identified_item']}")
    results = asyncio.run(_run_all_workers(state["identified_item"]))
    print(f"[SWARM] All {len(results)} workers completed.")
    return {**state, "swarm_results": list(results)}


# ---------------------------------------------------------------------------
# Node 3 — Synthesis (Claude Opus 4.6) → ElevenLabs schema
# ---------------------------------------------------------------------------

_ELEVENLABS_SCHEMA = """\
{
  "item_name": "string — the identified item (brand, model, year, condition)",
  "estimated_market_value": "string — synthesized price range, e.g. '$2,900 – $3,300'",
  "market_sentiment": "string — 2-3 sentence summary of Reddit/Twitter liquidity and demand signals",
  "target_shops": [
    {"name": "string", "address": "string", "phone": "string"},
    {"name": "string", "address": "string", "phone": "string"},
    {"name": "string", "address": "string", "phone": "string"}
  ],
  "negotiation_strategy": "string — a script for the voice agent: how to open the call, the target anchor price, and acceptable concession thresholds"
}"""


def synthesis_node(state: AgentState) -> AgentState:
    """
    Feed all swarm results into Claude Opus 4.6 and produce a strict
    ElevenLabs voice-agent JSON payload.
    """
    print("\n[SYNTHESIS] Claude Opus 4.6 is producing the ElevenLabs payload...")

    swarm_json = json.dumps(state["swarm_results"], indent=2)

    system_prompt = (
        "You are a resale intelligence engine producing a structured briefing for an ElevenLabs voice agent. "
        "Synthesize the swarm data provided and return ONLY a single valid JSON object that exactly "
        "matches the schema below. Do not include any text, commentary, or markdown outside the JSON object.\n\n"
        f"Required schema:\n{_ELEVENLABS_SCHEMA}"
    )

    user_message = (
        f"Identified item: {state['identified_item']}\n\n"
        f"Swarm intelligence data:\n{swarm_json}"
    )

    response = anthropic_client.messages.create(
        model="claude-opus-4-6",
        max_tokens=2048,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    raw = _strip_fences(response.content[0].text)

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        payload = {"raw": raw}

    print("[SYNTHESIS] ElevenLabs payload ready.")
    return {**state, "final_payload": payload}


# ---------------------------------------------------------------------------
# Build the LangGraph StateGraph
# ---------------------------------------------------------------------------


def build_graph() -> Any:
    graph = StateGraph(AgentState)

    graph.add_node("vision", vision_node)
    graph.add_node("swarm", swarm_node)
    graph.add_node("synthesis", synthesis_node)

    graph.set_entry_point("vision")
    graph.add_edge("vision", "swarm")
    graph.add_edge("swarm", "synthesis")
    graph.add_edge("synthesis", END)

    return graph.compile()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    # Update this path to point at the item image you want to appraise
    test_image_path = "sample_item.jpg"

    print("=" * 60)
    print("Vision-to-Swarm Ensemble Agent")
    print("=" * 60)
    print(f"Image: {test_image_path}\n")

    app = build_graph()

    initial_state: AgentState = {
        "image_path": test_image_path,
        "identified_item": "",
        "swarm_results": [],
        "final_payload": {},
    }

    final_state = app.invoke(initial_state)

    print("\n" + "=" * 60)
    print("ELEVENLABS PAYLOAD")
    print("=" * 60)
    print(json.dumps(final_state["final_payload"], indent=2))
    print("=" * 60)

    return final_state


if __name__ == "__main__":
    main()

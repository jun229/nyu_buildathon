"""
Hub-and-Spoke Ensemble Agent
============================
Hub (Orchestrator):  Claude Opus 4.6  — plans searches & aggregates results
Spokes (Sub-agents): NVIDIA Nemotron  — execute searches in parallel via asyncio.gather()
Graph:               LangGraph StateGraph (async)
"""

import asyncio
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
# Graph State
# ---------------------------------------------------------------------------


class AgentState(TypedDict):
    user_query: str                   # original user question
    search_tasks: list[dict[str, str]]  # planner output — list of {marketplace, url, task}
    spoke_results: list[dict[str, Any]]  # raw sub-agent outputs
    final_summary: str                # aggregator output


# ---------------------------------------------------------------------------
# Node 1 — Planner (Claude Opus 4.6)
# ---------------------------------------------------------------------------


def planner_node(state: AgentState) -> AgentState:
    """
    Ask Claude Opus to decompose the user query into 3 marketplace search tasks.
    Returns a JSON array written into state["search_tasks"].
    """
    print("\n[PLANNER] Claude Opus is planning search tasks...")

    system_prompt = (
        "You are a market research planner. "
        "Given a user query, produce exactly 3 search tasks for different online marketplaces. "
        "Return ONLY a valid JSON array with objects that each have these keys:\n"
        "  - marketplace (string): name of the marketplace\n"
        "  - url (string): a realistic mock URL for the search\n"
        "  - task (string): a one-sentence description of what to extract\n"
        "Do not include any text outside the JSON array."
    )

    response = anthropic_client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": state["user_query"]}],
    )

    raw = response.content[0].text.strip()

    # Strip optional markdown fences
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    search_tasks: list[dict[str, str]] = json.loads(raw)
    print(f"[PLANNER] Generated {len(search_tasks)} search tasks:")
    for t in search_tasks:
        print(f"  • {t['marketplace']}: {t['url']}")

    return {**state, "search_tasks": search_tasks}


# ---------------------------------------------------------------------------
# Node 2 — Parallel Executors (NVIDIA Nemotron via AsyncOpenAI)
# ---------------------------------------------------------------------------


async def _run_spoke(task: dict[str, str]) -> dict[str, Any]:
    """Call a single Nemotron sub-agent to extract price data from a mock search result."""

    mock_page_content = (
        f"Mock search results from {task['marketplace']} ({task['url']}):\n"
        "Listing 1: $3,299.00 — 2024 Specialized Stumpjumper Comp Alloy (Medium)\n"
        "Listing 2: $3,150.00 — 2024 Specialized Stumpjumper Expert Carbon (Large) — used\n"
        "Listing 3: $3,499.99 — 2024 Specialized Stumpjumper EVO Expert (Small) — new\n"
        "Listing 4: $2,899.00 — 2024 Specialized Stumpjumper Comp Carbon (Medium) — like new\n"
    )

    user_message = (
        f"Task: {task['task']}\n\n"
        f"Marketplace: {task['marketplace']}\n"
        f"URL: {task['url']}\n\n"
        f"Page content:\n{mock_page_content}\n\n"
        "Extract all prices and listings. Return a JSON object with keys:\n"
        "  - marketplace (string)\n"
        "  - listings (array of objects with 'title', 'price', 'condition')\n"
        "  - lowest_price (number)\n"
        "  - highest_price (number)\n"
        "Return ONLY valid JSON, no extra text."
    )

    print(f"  [SPOKE] Querying Nemotron for {task['marketplace']}...")

    completion = await nvidia_client.chat.completions.create(
        model="nvidia/nemotron-3-nano-30b-a3b",
        messages=[{"role": "user", "content": user_message}],
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

    # Parse JSON from content; fall back to raw string on failure
    content_output = content_output.strip()
    if content_output.startswith("```"):
        content_output = content_output.split("```")[1]
        if content_output.startswith("json"):
            content_output = content_output[4:]
        content_output = content_output.strip()

    try:
        parsed = json.loads(content_output)
    except json.JSONDecodeError:
        parsed = {"raw": content_output}

    return {
        "marketplace": task["marketplace"],
        "result": parsed,
        "reasoning_length": len(reasoning_output),
    }


async def _run_all_spokes(tasks: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Execute all spoke sub-agents concurrently."""
    return await asyncio.gather(*[_run_spoke(t) for t in tasks])


def executor_node(state: AgentState) -> AgentState:
    """Sync wrapper that runs the async spoke fan-out via asyncio.run()."""
    print("\n[EXECUTORS] Launching parallel Nemotron sub-agents...")
    results = asyncio.run(_run_all_spokes(state["search_tasks"]))
    print(f"[EXECUTORS] Received results from {len(results)} sub-agents.")
    return {**state, "spoke_results": list(results)}


# ---------------------------------------------------------------------------
# Node 3 — Aggregator (Claude Opus 4.6)
# ---------------------------------------------------------------------------


def aggregator_node(state: AgentState) -> AgentState:
    """
    Feed all spoke results back to Claude Opus for a final human-readable summary.
    """
    print("\n[AGGREGATOR] Claude Opus is synthesizing results...")

    results_json = json.dumps(state["spoke_results"], indent=2)

    system_prompt = (
        "You are a market research analyst. "
        "Given structured price data collected from multiple marketplaces, "
        "produce a concise, friendly summary that highlights:\n"
        "  1. The overall price range across all marketplaces\n"
        "  2. The best deals found\n"
        "  3. Any notable differences between marketplaces\n"
        "  4. A recommendation for the buyer\n"
        "Keep the summary under 300 words."
    )

    user_message = (
        f"Original query: {state['user_query']}\n\n"
        f"Marketplace data collected:\n{results_json}"
    )

    response = anthropic_client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    summary = response.content[0].text.strip()
    return {**state, "final_summary": summary}


# ---------------------------------------------------------------------------
# Build the LangGraph StateGraph
# ---------------------------------------------------------------------------


def build_graph() -> Any:
    graph = StateGraph(AgentState)

    graph.add_node("planner", planner_node)
    graph.add_node("executors", executor_node)
    graph.add_node("aggregator", aggregator_node)

    graph.set_entry_point("planner")
    graph.add_edge("planner", "executors")
    graph.add_edge("executors", "aggregator")
    graph.add_edge("aggregator", END)

    return graph.compile()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    test_query = "Find prices for a 2024 Specialized Stumpjumper mountain bike"

    print("=" * 60)
    print("Hub-and-Spoke Ensemble Agent")
    print("=" * 60)
    print(f"Query: {test_query}\n")

    app = build_graph()

    initial_state: AgentState = {
        "user_query": test_query,
        "search_tasks": [],
        "spoke_results": [],
        "final_summary": "",
    }

    final_state = app.invoke(initial_state)

    print("\n" + "=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)
    print(final_state["final_summary"])
    print("=" * 60)

    return final_state


if __name__ == "__main__":
    main()

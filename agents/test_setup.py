"""
Quick validation script — verifies API keys, connections, and image loading
without running the full pipeline.

Usage:
  python test_setup.py
  python test_setup.py --full sample_item.jpg   # also does a mini vision test
"""

import json
import os
import sys

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _SCRIPT_DIR)

from dotenv import load_dotenv

load_dotenv(os.path.join(_SCRIPT_DIR, ".env"))


def _ok(msg: str):
    print(f"  [OK] {msg}")


def _warn(msg: str):
    print(f"  [WARN] {msg}")


def _fail(msg: str):
    print(f"  [FAIL] {msg}")


def test_env():
    """Check that required environment variables are set."""
    print("\n--- Environment Variables ---")

    ant_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if ant_key and ant_key.startswith("sk-ant-"):
        _ok(f"ANTHROPIC_API_KEY set ({ant_key[:12]}...)")
    elif ant_key:
        _warn(f"ANTHROPIC_API_KEY set but doesn't start with 'sk-ant-' — may be invalid")
    else:
        _fail("ANTHROPIC_API_KEY not set")

    nv_key = os.environ.get("NVIDIA_API_KEY", "")
    if nv_key and nv_key.startswith("nvapi-"):
        _ok(f"NVIDIA_API_KEY set ({nv_key[:10]}...)")
    elif nv_key:
        _warn(f"NVIDIA_API_KEY set but doesn't start with 'nvapi-' — may be invalid")
    else:
        _fail("NVIDIA_API_KEY not set")

    sa_key = os.environ.get("SEARCHAPI_KEY", "")
    if sa_key:
        _ok(f"SEARCHAPI_KEY set ({sa_key[:8]}...)")
    else:
        _fail("SEARCHAPI_KEY not set — needed for Google Maps shop search")


def test_image():
    """Check that the sample image exists and can be loaded."""
    print("\n--- Image Loading ---")

    from agent import _image_to_base64

    sample = os.path.join(_SCRIPT_DIR, "sample_item.jpg")
    if not os.path.isfile(sample):
        _warn(f"No sample_item.jpg found in {_SCRIPT_DIR}")
        _warn("Place an item photo there or pass a path when running the agent")
        return False

    data, mime = _image_to_base64(sample)
    size_kb = len(data) * 3 / 4 / 1024  # approximate original size
    _ok(f"sample_item.jpg loaded ({size_kb:.0f} KB, {mime})")
    return True


def test_claude():
    """Verify Claude API connection."""
    print("\n--- Claude API ---")

    import anthropic

    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        _fail("Skipping — no API key")
        return False

    try:
        client = anthropic.Anthropic(api_key=key)
        resp = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=50,
            messages=[{"role": "user", "content": "Respond with exactly: CONNECTION_OK"}],
        )
        text = resp.content[0].text.strip()
        if "CONNECTION_OK" in text:
            _ok(f"Claude API connected (model: {resp.model})")
        else:
            _warn(f"Claude responded but unexpected output: {text[:80]}")
        return True
    except anthropic.AuthenticationError:
        _fail("Authentication failed — check your ANTHROPIC_API_KEY")
        return False
    except Exception as e:
        _fail(f"Claude API error: {e}")
        return False


def test_nvidia():
    """Verify NVIDIA API connection."""
    print("\n--- NVIDIA Nemotron API ---")

    from openai import OpenAI

    key = os.environ.get("NVIDIA_API_KEY")
    if not key:
        _fail("Skipping — no API key")
        return False

    try:
        client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=key,
        )
        resp = client.chat.completions.create(
            model="nvidia/nemotron-3-nano-30b-a3b",
            messages=[{"role": "user", "content": "What is 2+2? Reply with just the number."}],
            max_tokens=100,
            temperature=0.3,
        )
        content = resp.choices[0].message.content or ""
        reasoning = getattr(resp.choices[0].message, "reasoning_content", "") or ""
        if content.strip() or reasoning.strip():
            _ok(f"NVIDIA API connected (model: {resp.model}, content: {content.strip()[:40]})")
        else:
            _warn("NVIDIA responded but with empty content")
        return True
    except Exception as e:
        _fail(f"NVIDIA API error: {e}")
        return False


def test_searchapi():
    """Verify SearchAPI.io Google Maps connection."""
    print("\n--- SearchAPI.io Google Maps ---")

    import requests

    key = os.environ.get("SEARCHAPI_KEY")
    if not key:
        _fail("Skipping — no SEARCHAPI_KEY")
        return False

    try:
        r = requests.get(
            "https://www.searchapi.io/api/v1/search",
            params={
                "engine": "google_maps",
                "q": "pawn shop near New York",
                "api_key": key,
            },
            timeout=15,
        )
        if r.status_code == 200:
            results = r.json().get("local_results", [])
            if results:
                name = results[0].get("title", "?")
                phone = results[0].get("phone", "no phone")
                _ok(f"SearchAPI connected (found: {name}, {phone})")
            else:
                _warn("SearchAPI responded but returned no local_results")
            return True
        else:
            _fail(f"HTTP {r.status_code}: {r.text[:200]}")
            return False
    except Exception as e:
        _fail(f"SearchAPI error: {e}")
        return False


def test_langgraph():
    """Verify LangGraph can build the graph."""
    print("\n--- LangGraph ---")

    try:
        from agent import build_graph

        app = build_graph()
        _ok("Graph compiled successfully")
        return True
    except Exception as e:
        _fail(f"Graph build failed: {e}")
        return False


def main():
    print("=" * 50)
    print("  Appraisal Agent — Setup Validation")
    print("=" * 50)

    test_env()
    test_image()

    # API connection tests
    claude_ok = test_claude()
    nvidia_ok = test_nvidia()
    searchapi_ok = test_searchapi()
    graph_ok = test_langgraph()

    # Summary
    print("\n" + "=" * 50)
    print("  Summary")
    print("=" * 50)

    all_ok = claude_ok and nvidia_ok and searchapi_ok and graph_ok
    if all_ok:
        print("  All systems GO — ready to run the full pipeline.")
    else:
        print("  Some systems failed. Fix the issues above before running the agent.")

    print("=" * 50)

    # Handle --full flag for mini vision test
    if len(sys.argv) > 1 and sys.argv[1] == "--full":
        image = sys.argv[2] if len(sys.argv) > 2 else "sample_item.jpg"
        print(f"\n--- Full Pipeline Test with {image} ---")
        from agent import run

        run(image_path=image, location="New York, NY")


if __name__ == "__main__":
    main()

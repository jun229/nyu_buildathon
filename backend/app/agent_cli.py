import os
import json
import base64
import asyncio
import queue
import threading
import pyaudio
import httpx
import anthropic
from dotenv import load_dotenv
import websockets

FORMAT = pyaudio.paInt16
CHANNELS = 1
INPUT_RATE = 16000
OUTPUT_RATE = 16000
CHUNK = 1024
SILENCE_CHUNK = bytes(CHUNK * 2)  # 16-bit PCM silence (all zeros)

load_dotenv()


def _speaker_thread(
    speaker_stream: pyaudio.Stream,
    audio_q: queue.Queue,
    stop: threading.Event,
    agent_speaking: threading.Event,
):
    """Write audio to speaker. Sets agent_speaking while audio is queued/playing."""
    while not stop.is_set():
        try:
            data = audio_q.get(timeout=0.15)
            agent_speaking.set()
            speaker_stream.write(data)
        except queue.Empty:
            # Queue drained — agent finished speaking
            agent_speaking.clear()
        except Exception as e:
            if not stop.is_set():
                print(f"[Speaker] {e}")
            break


async def _resolve_conversation_id(
    client: httpx.AsyncClient,
    api_key: str,
    agent_id: str,
    hint: str | None,
) -> str | None:
    """
    Return a conversation_id to analyze.
    - If hint is provided (captured from the WebSocket session), use it directly.
    - Otherwise query the conversations list for the agent and pick the most recent one.
    """
    if hint:
        return hint

    print("[Analysis] No conversation ID from session — fetching latest from agent history...")
    r = await client.get(
        "https://api.elevenlabs.io/v1/convai/conversations",
        headers={"xi-api-key": api_key},
        params={"agent_id": agent_id, "page_size": 1},
    )
    if r.status_code != 200:
        print(f"[Analysis] Could not list conversations: HTTP {r.status_code}")
        return None
    conversations = r.json().get("conversations", [])
    if not conversations:
        print("[Analysis] No conversations found for this agent.")
        return None
    return conversations[0]["conversation_id"]


async def fetch_and_analyze(conversation_id_hint: str | None) -> None:
    """
    Resolve the target conversation (from WebSocket capture or agent history),
    poll until the transcript is ready (status == 'done'), then use Claude Haiku
    to extract:
      - owner_name
      - willing_to_sell (bool)
      - offered_price (float or null)
    """
    api_key = os.getenv("ELEVENLABS_API_KEY")
    agent_id = os.getenv("ELEVENLABS_AGENT_ID")

    # Bug fix: guard against missing env vars before making any API calls
    if not api_key:
        print("[Analysis] ELEVENLABS_API_KEY not set — skipping analysis.")
        return
    if not agent_id:
        print("[Analysis] ELEVENLABS_AGENT_ID not set — skipping analysis.")
        return

    conv_data: dict = {}
    async with httpx.AsyncClient() as client:
        conversation_id = await _resolve_conversation_id(
            client, api_key, agent_id, conversation_id_hint
        )
        if not conversation_id:
            return

        print(f"\n[Analysis] Waiting for transcript (conversation: {conversation_id})...")

        for _ in range(20):  # poll up to ~40 seconds
            await asyncio.sleep(2)
            r = await client.get(
                f"https://api.elevenlabs.io/v1/convai/conversations/{conversation_id}",
                headers={"xi-api-key": api_key},
            )
            if r.status_code != 200:
                print(f"[Analysis] Error fetching transcript: HTTP {r.status_code}")
                return
            conv_data = r.json()
            if conv_data.get("status") == "done":
                break
        else:
            print("[Analysis] Timed out waiting for transcript to be processed.")
            return

    transcript = conv_data.get("transcript", [])
    if not transcript:
        print("[Analysis] No transcript found in conversation.")
        return

    # Build plain-text transcript for Claude
    text = "\n".join(
        f"{t.get('role', '?')}: {t.get('message', '')}" for t in transcript
    )

    claude = anthropic.Anthropic()
    resp = claude.messages.create(
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
        result = json.loads(resp.content[0].text)
        willing = bool(result.get("willing_to_sell", False))
        price = result.get("offered_price")

        print("\n--- Conversation Insights ---")
        print(f"Owner Name:      {result.get('owner_name') or 'Unknown'}")
        print(f"Willing to Sell: {'Yes' if willing else 'No'}")
        print(f"Offered Price:   {'$' + str(price) if willing and price is not None else 'N/A'}")
        print("-----------------------------\n")
    except Exception as e:
        print(f"[Analysis] Failed to parse Claude response: {e}")
        print(f"[Analysis] Raw response: {resp.content[0].text}")


async def conversation_loop() -> str | None:
    """
    Run the live voice conversation and return the captured conversation_id
    (or None if it was never received) so the caller can run analysis.
    """
    api_key = os.getenv("ELEVENLABS_API_KEY")
    agent_id = os.getenv("ELEVENLABS_AGENT_ID")

    if not api_key or not agent_id:
        print("Error: ELEVENLABS_API_KEY and ELEVENLABS_AGENT_ID must be set.")
        return None

    url = f"wss://api.elevenlabs.io/v1/convai/conversation?agent_id={agent_id}"

    pa = pyaudio.PyAudio()
    mic_stream = pa.open(
        format=FORMAT, channels=CHANNELS, rate=INPUT_RATE,
        input=True, frames_per_buffer=CHUNK,
    )
    speaker_stream = pa.open(
        format=FORMAT, channels=CHANNELS, rate=OUTPUT_RATE,
        output=True, frames_per_buffer=CHUNK,
    )

    audio_q: queue.Queue = queue.Queue()
    stop_event = threading.Event()
    agent_speaking = threading.Event()  # gate: True while agent audio is playing

    spk_thread = threading.Thread(
        target=_speaker_thread,
        args=(speaker_stream, audio_q, stop_event, agent_speaking),
        daemon=True,
    )
    spk_thread.start()

    # Shared state for conversation ID captured during the session
    session: dict = {"conversation_id": None}

    try:
        async with websockets.connect(url, additional_headers={"xi-api-key": api_key}) as ws:
            print("\n--- Connected to ElevenLabs ---")
            print("Speak now (after the agent finishes). Press Ctrl+C to stop.\n")

            loop = asyncio.get_running_loop()

            async def send_audio():
                """Stream mic to ElevenLabs. Sends silence while agent is speaking to prevent echo."""
                try:
                    while True:
                        data = await loop.run_in_executor(
                            None,
                            lambda: mic_stream.read(CHUNK, exception_on_overflow=False),
                        )
                        # Gate: replace real mic audio with silence during agent speech.
                        chunk = SILENCE_CHUNK if agent_speaking.is_set() else data
                        await ws.send(json.dumps({
                            "user_audio_chunk": base64.b64encode(chunk).decode("utf-8")
                        }))
                except asyncio.CancelledError:
                    pass
                except websockets.exceptions.ConnectionClosed:
                    pass
                except Exception as e:
                    print(f"[Mic] {e}")

            async def receive_and_handle():
                try:
                    async for raw in ws:
                        msg = json.loads(raw)
                        event_type = msg.get("type")

                        if event_type == "conversation_initiation_metadata":
                            meta = msg.get("conversation_initiation_metadata_event", {})
                            session["conversation_id"] = meta.get("conversation_id")
                            print(
                                f"[Session] ID: {session['conversation_id']} | "
                                f"Format: {meta.get('agent_output_audio_format')}"
                            )

                        elif event_type == "audio":
                            b64 = msg.get("audio_event", {}).get("audio_base_64", "")
                            if b64:
                                audio_q.put(base64.b64decode(b64))

                        elif event_type == "agent_response":
                            text = msg.get("agent_response_event", {}).get("agent_response", "")
                            if text:
                                print(f"Agent: {text}")

                        elif event_type == "user_transcript":
                            text = msg.get("user_transcription_event", {}).get("user_transcript", "")
                            if text:
                                print(f"You:   {text}")

                        elif event_type == "interruption":
                            # User interrupted — stop playback immediately
                            agent_speaking.clear()
                            while not audio_q.empty():
                                try:
                                    audio_q.get_nowait()
                                except queue.Empty:
                                    break

                        elif event_type == "ping":
                            event_id = msg.get("ping_event", {}).get("event_id")
                            await ws.send(json.dumps({"type": "pong", "event_id": event_id}))

                        elif event_type == "client_tool_call":
                            call = msg.get("client_tool_call", {})
                            await ws.send(json.dumps({
                                "type": "client_tool_result",
                                "tool_call_id": call.get("tool_call_id"),
                                "result": "{}",
                                "is_error": False,
                            }))

                except asyncio.CancelledError:
                    pass
                except websockets.exceptions.ConnectionClosed:
                    print("\n[Session] Connection closed.")
                except Exception as e:
                    print(f"[Receive] {e}")

            tasks = [
                asyncio.create_task(send_audio()),
                asyncio.create_task(receive_and_handle()),
            ]
            try:
                await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            finally:
                for t in tasks:
                    t.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)

    except websockets.exceptions.WebSocketException as e:
        print(f"[Connection] WebSocket error: {e}")
    except Exception as e:
        print(f"[Connection] {e}")
    finally:
        stop_event.set()
        spk_thread.join(timeout=2)
        mic_stream.stop_stream()
        mic_stream.close()
        speaker_stream.stop_stream()
        speaker_stream.close()
        pa.terminate()

    return session["conversation_id"]


if __name__ == "__main__":
    # Bug fix: capture conversation_id from the loop so fetch_and_analyze
    # runs even when the user ends the call with Ctrl+C.
    captured_id: str | None = None
    try:
        captured_id = asyncio.run(conversation_loop())
    except KeyboardInterrupt:
        print("\nSession ended.")

    # Always analyze — falls back to latest conversation if captured_id is None
    try:
        asyncio.run(fetch_and_analyze(captured_id))
    except KeyboardInterrupt:
        pass

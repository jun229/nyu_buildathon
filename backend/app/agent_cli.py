import os
import json
import base64
import asyncio
import queue
import threading
import pyaudio
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


async def conversation_loop():
    api_key = os.getenv("ELEVENLABS_API_KEY")
    agent_id = os.getenv("ELEVENLABS_AGENT_ID")

    if not api_key or not agent_id:
        print("Error: ELEVENLABS_API_KEY and ELEVENLABS_AGENT_ID must be set.")
        return

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
                        # This prevents the speaker output from being transcribed as user input.
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
                            print(
                                f"[Session] ID: {meta.get('conversation_id')} | "
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


if __name__ == "__main__":
    try:
        asyncio.run(conversation_loop())
    except KeyboardInterrupt:
        print("\nSession ended.")

# server.py
from fastapi import FastAPI, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import whisper
import tempfile
import os



import threading
import time
import queue
import sounddevice as sd
import numpy as np
import whisper
from fastapi import Query
from urllib.parse import unquote
import datetime
import json

SAMPLE_RATE = 16000
CHUNK_SECONDS = 3
# DEVICE_INDEX = None   # None = default input; set to loopback device if you want system audio
DEVICE_INDEX = next(i for i, d in enumerate(sd.query_devices()) if "CABLE Output" in d["name"])
# shared queue for audio chunks
_audio_q = queue.Queue()
# load whisper model once
_whisper_model = whisper.load_model("base")

live_transcript = []  # global list to hold timestamped text


def _audio_callback(indata, frames, time_info, status):
    # called by sounddevice whenever new audio arrives
    _audio_q.put(indata.copy())

def _transcribe_worker():
    """Continuously pull audio from the queue and transcribe it."""
    print("🔊 Audio capture thread started.")
    buffer = np.zeros((0, 1), dtype=np.float32)
    chunk_samples = SAMPLE_RATE * CHUNK_SECONDS
    while True:
        try:
            data = _audio_q.get(timeout=1)
            buffer = np.concatenate((buffer, data))
            if len(buffer) >= chunk_samples:
                segment = np.squeeze(buffer[:chunk_samples])
                buffer = buffer[chunk_samples:]
                result = _whisper_model.transcribe(segment, fp16=False)
                text = result["text"].strip()
                if text:
                    ts = datetime.datetime.now().isoformat(timespec='seconds')
                    entry = {"timestamp": ts, "text": text}
                    live_transcript.append(entry)
                    print(f"[{ts}] {text}")
        except queue.Empty:
            continue



def _capture_loop():
    with sd.InputStream(
        channels=1,
        samplerate=SAMPLE_RATE,
        device=DEVICE_INDEX,
        callback=_audio_callback,
        dtype="float32"
    ):
        print("🎙  Listening... (Ctrl+C to stop server)")
        while True:
            time.sleep(1)

app = FastAPI()
# Load model once at startup (choose "base", "small", "medium", "large")
whisper_model = whisper.load_model("small")  # good balance for CPU-only

@app.get("/live")
def get_live(since: str = Query(None, description="ISO timestamp to get entries after")):
    """
    Return transcript entries after a given timestamp.
    Example: /live?since=2025-10-15T12:58:42
    """
    try:
        if since:
            # decode URL encoding first
            since_decoded = unquote(since)
            # ensure it's an ISO datetime
            since_dt = datetime.fromisoformat(since_decoded)
            filtered = [
                t for t in live_transcript
                if datetime.fromisoformat(t["timestamp"]) > since_dt
            ]
            return {"segments": filtered}
        else:
            # default to last 100 if no timestamp given
            return {"segments": live_transcript[-100:]}
    except Exception as e:
        print("Error parsing 'since':", e)
        return {"error": f"Invalid 'since' value: {since}"}

@app.on_event("startup")
def start_audio_streamer():
    """Start both the capture stream and the transcription thread."""
    threading.Thread(target=_transcribe_worker, daemon=True).start()
    threading.Thread(target=_capture_loop, daemon=True).start()

@app.on_event("shutdown")
def save_transcript_on_shutdown():
    if not live_transcript:
        return
    timestamp = datetime.datetime.now().isoformat(timespec='seconds').replace(":", "-")
    filename = f"transcript_live_{timestamp}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(live_transcript, f, ensure_ascii=False, indent=2)
    print(f"💾 Transcript saved to {filename}")

client = OpenAI()  # uses your OPENAI_API_KEY env variable
# Allow requests from local browser
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # for local dev only
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    # Save temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    # Transcribe
    result = whisper_model.transcribe(tmp_path, fp16=False)
    os.remove(tmp_path)

    # Build response (keep only text + segments)
    response = {
        "text": result["text"].strip(),
        "segments": [
            {"start": seg["start"], "end": seg["end"], "text": seg["text"].strip()}
            for seg in result["segments"]
        ],
    }
    return response


@app.post("/ask")
async def ask_ai(request: Request):
    data = await request.json()
    question = data.get("question", "")

    if not question.strip():
        return {"answer": "(No question text received)"}

    return {"answer": "Hello from FastAPI! This is a placeholder response."}

    # Call OpenAI model (you can change to gpt-4o, etc.)
    # completion = client.chat.completions.create(
    #     model="gpt-4o-mini",
    #     messages=[
    #         {"role": "system", "content": "You are an assistant answering transcript-related questions."},
    #         {"role": "user", "content": question}
    #     ]
    # )

    # answer = completion.choices[0].message.content
    # return {"answer": answer}
